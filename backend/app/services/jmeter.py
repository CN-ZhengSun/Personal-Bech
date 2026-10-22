"""Single-host JMeter runner with immutable inputs and durable JSON/artifacts."""
import csv
from collections import Counter
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET

from pydantic import BaseModel, Field, HttpUrl

from app.services.jmeter_process import ProcessJob

ROOT = Path(__file__).resolve().parents[2] / "runtime" / "jmeter"
_lock = threading.RLock()
_active = None
_stops = {}
ACTIVE_STATES = {"starting", "running", "reporting", "stopping"}


class ScenarioRequest(BaseModel):
    project_id: int = Field(gt=0)
    url: HttpUrl = "http://127.0.0.1:8000/health"


class RunRequest(BaseModel):
    project_id: int = Field(gt=0)
    script_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    name: str = Field(default="性能测试", min_length=1, max_length=100)
    threads: int = Field(default=5, ge=1, le=200)
    ramp_seconds: int = Field(default=5, ge=0, le=600)
    duration_seconds: int = Field(default=30, ge=1, le=3600)
    environment: str = Field(default="", max_length=100)
    version: str = Field(default="", max_length=100)
    max_error_rate: float = Field(default=1, ge=0, le=100)
    max_p95_ms: int = Field(default=1000, ge=1, le=600000)


def now():
    return datetime.now(timezone.utc).isoformat()


def record_dir(kind, record_id):
    if kind not in {"scripts", "runs"} or not re.fullmatch(r"[a-f0-9]{32}", record_id):
        raise ValueError("记录编号无效")
    return (ROOT / kind / record_id).resolve()


def write_record(kind, record):
    folder = record_dir(kind, record["id"])
    folder.mkdir(parents=True, exist_ok=True)
    with _lock:
        temp = folder / "metadata.tmp"
        temp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        temp.replace(folder / "metadata.json")


def read_record(kind, record_id):
    with _lock:
        record = json.loads((record_dir(kind, record_id) / "metadata.json").read_text(encoding="utf-8"))
        if kind == "runs" and record["state"] in ACTIVE_STATES and record_id != _active:
            record.update(state="interrupted", message="服务重启，运行已中断", finished_at=now())
            write_record(kind, record)
        return record


def list_records(kind, project_id):
    records = []
    for path in (ROOT / kind).glob("*/metadata.json"):
        try:
            record = read_record(kind, path.parent.name)
            if record["project_id"] == project_id:
                records.append(record)
        except (OSError, ValueError):
            continue
    return sorted(records, key=lambda x: x["created_at"], reverse=True)


def jmeter_home():
    return Path(os.environ.get("JMETER_HOME") or Path(__file__).resolve().parents[3] / "tools/apache-jmeter-5.6.3")


def java_binary():
    java_home = os.environ.get("JAVA_HOME")
    binary = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java") if java_home else None
    return str(binary) if binary and binary.is_file() else shutil.which("java")


def capabilities():
    ready = (jmeter_home() / "bin/ApacheJMeter.jar").is_file() and bool(java_binary())
    return {"ready": ready, "engine": "Apache JMeter", "max_threads": 200,
            "active_run": _active, "message": "本机引擎就绪" if ready else "请检查 JMeter 安装目录及 Java 环境"}


def save_script(project_id, uploads):
    names = [name for name, _ in uploads]
    if len(set(n.casefold() for n in names)) != len(names) or any(not re.fullmatch(r"[\w .-]{1,120}", n) or n.startswith(".") for n in names):
        raise ValueError("文件名不能重复或包含路径及特殊字符")
    if any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", n.split(".")[0]) for n in names):
        raise ValueError("请勿使用系统保留文件名")
    if any(n.casefold() in {"metadata.json", "metadata.tmp", "results.jtl", "console.log", "jmeter.log"} for n in names):
        raise ValueError("文件名与运行文件冲突")
    jmx = [(name, data) for name, data in uploads if name.lower().endswith(".jmx")]
    if len(jmx) != 1 or any(Path(n).suffix.lower() not in {".jmx", ".csv"} for n in names):
        raise ValueError("请提供一个 JMX 文件及可选的 CSV 文件")
    data = jmx[0][1]
    normalized = data.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in normalized or b"<!ENTITY" in normalized:
        raise ValueError("JMX 不允许包含 DTD 或实体声明")
    try:
        tree = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("JMX 不是有效的 XML") from exc
    if tree.tag != "jmeterTestPlan":
        raise ValueError("文件不是 JMeter 测试计划")
    if any(p.attrib.get("name") == "filename" and p.text and
           (":" in p.text or "\\" in p.text or "/" in p.text or p.text.startswith("."))
           for p in tree.iter("stringProp")):
        raise ValueError("数据文件请使用同目录文件名，并一并上传")
    record = {"id": uuid4().hex, "project_id": project_id, "name": jmx[0][0],
              "files": names, "created_at": now(),
              "parameterized": all(("__P(" + key) in ET.tostring(tree, encoding="unicode")
                                   for key in ("threads", "ramp_seconds", "duration_seconds"))}
    folder = record_dir("scripts", record["id"])
    folder.mkdir(parents=True)
    for name, content in uploads:
        (folder / name).write_bytes(content)
    write_record("scripts", record)
    return record


def http_template(url="http://127.0.0.1:8000/health"):
    parsed = urlsplit(str(url))
    root = ET.Element("jmeterTestPlan", version="1.2", properties="5.0", jmeter="5.6.3")
    outer = ET.SubElement(root, "hashTree")
    plan = ET.SubElement(outer, "TestPlan", guiclass="TestPlanGui", testclass="TestPlan", testname="HTTP 场景", enabled="true")
    ET.SubElement(plan, "elementProp", name="TestPlan.user_defined_variables", elementType="Arguments", guiclass="ArgumentsPanel", testclass="Arguments", testname="用户变量")
    inner = ET.SubElement(outer, "hashTree")
    group = ET.SubElement(inner, "ThreadGroup", guiclass="ThreadGroupGui", testclass="ThreadGroup", testname="HTTP 并发", enabled="true")
    loop = ET.SubElement(group, "elementProp", name="ThreadGroup.main_controller", elementType="LoopController", guiclass="LoopControlPanel", testclass="LoopController", testname="循环")
    ET.SubElement(loop, "boolProp", name="LoopController.continue_forever").text = "false"
    ET.SubElement(loop, "stringProp", name="LoopController.loops").text = "-1"
    for name, value in {"ThreadGroup.num_threads": "${__P(threads,5)}", "ThreadGroup.ramp_time": "${__P(ramp_seconds,5)}", "ThreadGroup.duration": "${__P(duration_seconds,30)}", "ThreadGroup.on_sample_error": "continue"}.items():
        ET.SubElement(group, "stringProp", name=name).text = value
    ET.SubElement(group, "boolProp", name="ThreadGroup.scheduler").text = "true"
    samples = ET.SubElement(inner, "hashTree")
    sampler = ET.SubElement(samples, "HTTPSamplerProxy", guiclass="HttpTestSampleGui", testclass="HTTPSamplerProxy", testname="HTTP 请求", enabled="true")
    for name, value in {"HTTPSampler.domain": parsed.hostname or "127.0.0.1", "HTTPSampler.port": str(parsed.port or ""), "HTTPSampler.protocol": parsed.scheme, "HTTPSampler.path": (parsed.path or "/") + ("?" + parsed.query if parsed.query else ""), "HTTPSampler.method": "GET", "HTTPSampler.connect_timeout": "5000", "HTTPSampler.response_timeout": "10000"}.items():
        ET.SubElement(sampler, "stringProp", name=name).text = value
    ET.SubElement(sampler, "boolProp", name="HTTPSampler.follow_redirects").text = "true"
    ET.SubElement(sampler, "boolProp", name="HTTPSampler.use_keepalive").text = "true"
    ET.SubElement(samples, "hashTree")
    timer = ET.SubElement(samples, "ConstantTimer", guiclass="ConstantTimerGui", testclass="ConstantTimer", testname="请求间隔", enabled="true")
    ET.SubElement(timer, "stringProp", name="ConstantTimer.delay").text = "100"
    ET.SubElement(samples, "hashTree")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


class Metrics:
    def __init__(self):
        self.offset = 0
        self.header = None
        self.count = self.errors = self.total = 0
        self.first = self.last = None
        self.histogram = Counter()

    def update(self, path):
        if path.exists():
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                stream.seek(self.offset)
                while True:
                    start = stream.tell()
                    line = stream.readline()
                    if not line or not line.endswith("\n"):
                        self.offset = start
                        break
                    self.offset = stream.tell()
                    row = next(csv.reader([line]))
                    if self.header is None:
                        self.header = row
                        continue
                    item = dict(zip(self.header, row))
                    try:
                        elapsed = int(item["elapsed"])
                        timestamp = int(item["timeStamp"])
                        success = item["success"].lower() == "true"
                    except (KeyError, ValueError):
                        continue
                    self.count += 1
                    self.errors += not success
                    self.total += elapsed
                    self.histogram[elapsed] += 1
                    self.first = min(self.first if self.first is not None else timestamp, timestamp)
                    self.last = max(self.last or 0, timestamp + elapsed)
        percentile = 0
        accumulated = 0
        for latency, count in sorted(self.histogram.items()):
            accumulated += count
            if accumulated >= math.ceil(self.count * .95):
                percentile = latency
                break
        return {"samples": self.count, "errors": self.errors,
                "error_rate": round(self.errors / self.count * 100, 2) if self.count else 0,
                "average_ms": round(self.total / self.count, 1) if self.count else 0,
                "p95_ms": percentile,
                "throughput": round(self.count / max(((self.last or 0) - (self.first or 0)) / 1000, .001), 2) if self.count else 0}


def command(*args):
    return [java_binary(), "-Xms128m", "-Xmx512m", "-Dfile.encoding=UTF-8", "-Duser.language=en", "-Duser.country=US", "-jar",
            str((jmeter_home() / "bin/ApacheJMeter.jar").resolve()), "-Jlanguage=en", *args]


def start_run(payload):
    global _active
    with _lock:
        if _active:
            raise ValueError("本机已有运行中的任务，请等待完成或先停止")
        if not capabilities()["ready"]:
            raise ValueError("JMeter 或 Java 未就绪")
        try:
            script = read_record("scripts", payload.script_id)
        except FileNotFoundError as exc:
            raise ValueError("脚本不存在") from exc
        if script["project_id"] != payload.project_id:
            raise ValueError("脚本不属于当前项目")
        if not script["parameterized"]:
            raise ValueError("脚本需通过 __P 读取 threads、ramp_seconds、duration_seconds；请先按模板修改")
        record = {**payload.model_dump(), "id": uuid4().hex, "script_name": script["name"],
                  "created_at": now(), "state": "starting", "message": "准备启动", "metrics": {},
                  "timeline": [], "report_ready": False, "verdict": "pending"}
        folder = record_dir("runs", record["id"])
        folder.mkdir(parents=True)
        for name in script["files"]:
            shutil.copyfile(record_dir("scripts", script["id"]) / name, folder / name)
        # Locale is initialized before -J options; use a per-run base config so the
        # bundled zh_CN translation's malformed percentile format is not used.
        properties = (jmeter_home() / "bin/jmeter.properties").read_text(encoding="utf-8")
        properties = re.sub(r"(?m)^language\s*=.*$", "language=en", properties)
        (folder / "engine.properties").write_text(properties + "\nlanguage=en\n", encoding="utf-8")
        _active = record["id"]
        _stops[_active] = threading.Event()
        write_record("runs", record)
        threading.Thread(target=_execute, args=(record,), daemon=True).start()
        return record.copy()


def terminate(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
    else:
        process.kill()
    process.wait(timeout=15)


def _execute(record):
    global _active
    folder = record_dir("runs", record["id"])
    stop = _stops[record["id"]]
    metrics = Metrics()
    process = None
    job = None
    try:
        job = ProcessJob()
        args = command("-p", str(folder / "engine.properties"), "-n", "-t", str(folder / record["script_name"]), "-l", str(folder / "results.jtl"),
                       "-j", str(folder / "jmeter.log"), "-Jjmeter.save.saveservice.output_format=csv",
                       "-Jjmeter.save.saveservice.print_field_names=true", "-Jjmeter.save.saveservice.timestamp_format=ms",
                       "-Jjmeter.save.saveservice.autoflush=true",
                       *[f"-J{key}={record[key]}" for key in ("threads", "ramp_seconds", "duration_seconds")])
        with (folder / "console.log").open("wb") as log:
            process = subprocess.Popen(args, cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            job.attach(process)
            record.update(state="running", started_at=now(), message="正在压测")
            deadline = time.monotonic() + record["duration_seconds"] + record["ramp_seconds"] + 60
            while process.poll() is None:
                record["metrics"] = metrics.update(folder / "results.jtl")
                record["timeline"] = (record["timeline"] + [{"at": now(), **record["metrics"]}])[-120:]
                write_record("runs", record)
                if stop.wait(1):
                    terminate(process)
                    record.update(state="stopped", message="已停止，保留已产生的结果")
                    break
                if time.monotonic() > deadline:
                    terminate(process)
                    record.update(state="failed", message="执行超时，请检查脚本的持续时间配置")
                    break
            record["metrics"] = metrics.update(folder / "results.jtl")
            if record["state"] == "running":
                if process.returncode != 0 or not record["metrics"]["samples"]:
                    record.update(state="failed", message="引擎执行失败或未产生采样，请查看运行日志")
                else:
                    record.update(state="reporting", message="正在生成 HTML 报告")
                    write_record("runs", record)
                    process = subprocess.Popen(command("-p", str(folder / "engine.properties"), "-g", str(folder / "results.jtl"), "-o", str(folder / "report")),
                                               cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    job.attach(process)
                    deadline = time.monotonic() + 180
                    while process.poll() is None:
                        if stop.wait(1) or time.monotonic() > deadline:
                            terminate(process)
                            break
                    record["report_ready"] = (folder / "report/index.html").is_file() and process.returncode == 0
                    if stop.is_set():
                        record.update(state="stopped", message="报告生成已停止")
                    else:
                        record.update(state="completed", message="压测完成" if record["report_ready"] else "压测完成，报告生成失败，请查看日志")
                        values = record["metrics"]
                        error_rate = metrics.errors / metrics.count * 100
                        record["verdict"] = "passed" if error_rate <= record["max_error_rate"] and values["p95_ms"] <= record["max_p95_ms"] else "failed"
    except Exception:
        logging.getLogger(__name__).exception("JMeter run %s failed", record["id"])
        if process is not None and process.poll() is None:
            terminate(process)
        record.update(state="failed", message="执行异常，请检查 Java 环境及运行日志")
    finally:
        if job:
            job.close()
        record["finished_at"] = now()
        with _lock:
            write_record("runs", record)
            _active = None
            _stops.pop(record["id"], None)


def stop_run(run_id):
    with _lock:
        record = read_record("runs", run_id)
        if run_id in _stops:
            _stops[run_id].set()
            record.update(state="stopping", message="正在停止运行")
            write_record("runs", record)
        return record
