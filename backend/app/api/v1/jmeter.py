from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project
from app.services import jmeter as service

router = APIRouter(prefix="/jmeter", tags=["jmeter"], dependencies=[Depends(get_current_user)])


def check_project(project_id: int, db: Session):
    if not db.get(Project, project_id):
        raise HTTPException(404, "项目不存在")


@router.get("/capabilities")
def capabilities():
    return service.capabilities()


@router.get("/scripts")
def scripts(project_id: int, db: Session = Depends(get_db)):
    check_project(project_id, db)
    return service.list_records("scripts", project_id)


@router.post("/scripts", status_code=201)
async def upload_script(project_id: int = Form(...), files: list[UploadFile] = File(...),
                        db: Session = Depends(get_db)):
    check_project(project_id, db)
    if not 1 <= len(files) <= 11:
        raise HTTPException(400, "请上传一个 JMX 和最多 10 个 CSV 文件")
    uploads = []
    for file in files:
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "单文件不能超过 10 MiB")
        uploads.append((file.filename or "", content))
    try:
        return service.save_script(project_id, uploads)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/template")
def template():
    return Response(service.http_template(), media_type="application/xml",
                    headers={"Content-Disposition": 'attachment; filename="http-scenario.jmx"'})


@router.post("/scenarios", status_code=201)
def scenario(payload: service.ScenarioRequest, db: Session = Depends(get_db)):
    check_project(payload.project_id, db)
    return service.save_script(payload.project_id, [("http-scenario.jmx", service.http_template(payload.url))])


@router.get("/runs")
def runs(project_id: int, db: Session = Depends(get_db)):
    check_project(project_id, db)
    return service.list_records("runs", project_id)


@router.post("/runs", status_code=202)
def create_run(payload: service.RunRequest, db: Session = Depends(get_db)):
    check_project(payload.project_id, db)
    try:
        return service.start_run(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def find_run(run_id: str):
    try:
        return service.read_record("runs", run_id)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "运行记录不存在")


@router.get("/runs/{run_id}")
def run(run_id: str):
    return find_run(run_id)


@router.post("/runs/{run_id}/stop")
def stop(run_id: str):
    find_run(run_id)
    return service.stop_run(run_id)


@router.get("/runs/{run_id}/log")
def log_tail(run_id: str):
    find_run(run_id)
    path = service.record_dir("runs", run_id) / "console.log"
    content = b""
    if path.is_file():
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 64000))
            content = stream.read(64000)
    return Response(content.decode("utf-8", errors="replace"), media_type="text/plain")


@router.get("/runs/{run_id}/files/{file_path:path}")
def artifact(run_id: str, file_path: str):
    find_run(run_id)
    root = service.record_dir("runs", run_id)
    target = (root / file_path).resolve()
    allowed = file_path in {"results.jtl", "jmeter.log", "console.log"} or file_path.startswith("report/")
    if file_path.startswith("report/"):
        allowed = (root / "report").resolve() in target.parents
    if not allowed or root not in target.parents or not target.is_file():
        raise HTTPException(404, "文件不存在或尚未生成")
    headers = {"X-Content-Type-Options": "nosniff"}
    if file_path.startswith("report/"):
        # Generated reports are trusted local artifacts of trusted JMX scripts.
        # Same-origin is required for authenticated CSS/JS and JMeter's cookies.
        headers["Content-Security-Policy"] = "sandbox allow-scripts allow-same-origin; default-src 'self' 'unsafe-inline' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
        headers["Referrer-Policy"] = "no-referrer"
    return FileResponse(target, headers=headers,
                        filename=Path(file_path).name if not file_path.startswith("report/") else None)
