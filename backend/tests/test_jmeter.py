import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import ValidationError

from app.services import jmeter as jm


@pytest.fixture
def storage(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, 'ROOT', tmp_path)
    yield tmp_path
    if jm._active:
        jm.stop_run(jm._active)
        deadline = time.monotonic() + 20
        while jm._active and time.monotonic() < deadline:
            time.sleep(.1)


@pytest.mark.parametrize('filename', ['../evil.jmx', 'C:\\evil.jmx', '/evil.jmx', '.hidden.jmx', 'CON.jmx'])
def test_reject_path_filenames(storage, filename):
    with pytest.raises(ValueError):
        jm.save_script(1, [(filename, jm.http_template())])


@pytest.mark.parametrize('data', [b'<no/>', b'garbage', b'<!DOCTYPE foo><jmeterTestPlan/>', '<!DOCTYPE foo><jmeterTestPlan/>'.encode('utf-16')])
def test_reject_invalid_xml(storage, data):
    with pytest.raises(ValueError):
        jm.save_script(1, [('plan.jmx', data)])


def test_immutable_script_and_project_filter(storage):
    script = jm.save_script(1, [('plan.jmx', jm.http_template()), ('data.csv', b'name\nx\n')])
    assert script['parameterized']
    assert len(jm.list_records('scripts', 1)) == 1
    assert jm.list_records('scripts', 2) == []
    assert (jm.record_dir('scripts', script['id']) / 'data.csv').read_bytes() == b'name\nx\n'
    with pytest.raises(ValueError, match='当前项目'):
        jm.start_run(jm.RunRequest(project_id=2, script_id=script['id']))


def test_metrics_incremental_and_partial_line(storage):
    path = storage / 'results.jtl'
    path.write_text('timeStamp,elapsed,success\n1000,10,true\n1100,100,false\n1200,30', encoding='utf-8')
    metrics = jm.Metrics()
    values = metrics.update(path)
    assert values['samples'] == 2
    assert values['error_rate'] == 50
    assert values['p95_ms'] == 100
    assert metrics.update(path) == values
    with path.open('a', encoding='utf-8') as stream:
        stream.write(',true\n')
    assert metrics.update(path)['samples'] == 3


def test_request_limits():
    for override in [{'threads': 201}, {'duration_seconds': 0}, {'max_error_rate': -1}, {'script_id': '../x'}]:
        with pytest.raises(ValidationError):
            jm.RunRequest(**{'project_id': 1, 'script_id': 'a' * 32, **override})


def test_restart_marks_interrupted(storage):
    record = dict(id='a' * 32, project_id=1, state='running', created_at=jm.now())
    jm.write_record('runs', record)
    assert jm.read_record('runs', record['id'])['state'] == 'interrupted'


def test_utf16_parameter_detection(storage):
    content = jm.http_template().decode('utf-8').replace("encoding='utf-8'", "encoding='utf-16'")
    assert jm.save_script(1, [('plan.jmx', content.encode('utf-16'))])['parameterized']


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, *args):
        pass


def wait_run(run_id, timeout=55):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = jm.read_record('runs', run_id)
        if record['state'] not in jm.ACTIVE_STATES:
            return record
        time.sleep(.3)
    raise AssertionError('Run did not finish')


@pytest.mark.skipif(not jm.capabilities()['ready'], reason='Local JMeter/Java not installed')
def test_real_jmeter_report_and_stop(storage):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        script = jm.save_script(1, [('plan.jmx', jm.http_template(f'http://127.0.0.1:{server.server_port}/test'))])
        payload = jm.RunRequest(project_id=1, script_id=script['id'], threads=1, ramp_seconds=0, duration_seconds=2)
        run = jm.start_run(payload)
        with pytest.raises(ValueError, match='已有'):
            jm.start_run(payload)
        result = wait_run(run['id'])
        console = (jm.record_dir('runs', run['id']) / 'console.log').read_text(encoding='utf-8', errors='replace')
        assert result['state'] == 'completed', console
        assert result['metrics']['samples'] > 0, console
        assert result['report_ready'], console
        assert result['verdict'] == 'passed'
        assert (jm.record_dir('runs', run['id']) / 'plan.jmx').read_bytes() == jm.http_template(f'http://127.0.0.1:{server.server_port}/test')
        payload.duration_seconds = 30
        second = jm.start_run(payload)
        time.sleep(2)
        jm.stop_run(second['id'])
        assert wait_run(second['id'])['state'] == 'stopped'
        assert jm._active is None
    finally:
        server.shutdown()


def test_authenticated_api_and_artifact_boundary(storage):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1 import jmeter as api
    from app.core.database import get_db
    from app.core.security import get_current_user

    class Database:
        def get(self, model, project_id):
            return object() if project_id == 1 else None

    app = FastAPI()
    app.include_router(api.router, prefix='/api/v1')
    app.dependency_overrides[get_db] = lambda: Database()
    with TestClient(app) as client:
        assert client.get('/api/v1/jmeter/capabilities').status_code == 401
        app.dependency_overrides[get_current_user] = lambda: object()
        assert client.get('/api/v1/jmeter/scripts?project_id=99').status_code == 404
        response = client.post('/api/v1/jmeter/scenarios', json={'project_id': 1, 'url': 'http://127.0.0.1:8000/health'})
        assert response.status_code == 201
        assert response.json()['parameterized']
        response = client.post('/api/v1/jmeter/scripts', data={'project_id': 1}, files=[('files', ('plan.jmx', jm.http_template(), 'application/xml'))])
        assert response.status_code == 201
        assert len(client.get('/api/v1/jmeter/scripts?project_id=1').json()) == 2
        record = dict(id='b' * 32, project_id=1, state='completed', created_at=jm.now())
        jm.write_record('runs', record)
        folder = jm.record_dir('runs', record['id'])
        (folder / 'console.log').write_text('hello', encoding='utf-8')
        (folder / 'report').mkdir()
        (folder / 'report/index.html').write_text('<html>report</html>', encoding='utf-8')
        base = f'/api/v1/jmeter/runs/{record["id"]}'
        assert client.get(base + '/log').text == 'hello'
        assert client.get(base + '/files/console.log').status_code == 200
        assert client.get(base + '/files/metadata.json').status_code == 404
        assert client.get(base + '/files/report/%2e%2e/metadata.json').status_code == 404
        report = client.get(base + '/files/report/index.html')
        assert report.status_code == 200
        assert "sandbox allow-scripts" in report.headers['Content-Security-Policy']
        assert "allow-same-origin" in report.headers['Content-Security-Policy']
        app.dependency_overrides.pop(get_current_user)
        assert client.get(base + '/files/report/index.html').status_code == 401
