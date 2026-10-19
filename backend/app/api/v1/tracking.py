import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_current_websocket_user
from app.models.project import Project
from app.models.tracking import TrackingConfig, TrackingEvent
from app.schemas.tracking import (
    TrackingConfigIn,
    TrackingConfigOut,
    TrackingEventCreate,
    TrackingEventOut,
    TrackingEventUpdate,
    TrackingIgnoreIn,
)
from app.services.tracking_collector import collector_manager, ws_manager

router = APIRouter(prefix="/tracking", tags=["tracking"], dependencies=[Depends(get_current_user)])


def _get_project(project_id: int, db: Session) -> Project:
    proj = db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return proj


def _get_config(project_id: int, db: Session) -> TrackingConfig:
    cfg = db.query(TrackingConfig).filter(TrackingConfig.project_id == project_id).first()
    if not cfg:
        cfg = TrackingConfig(project_id=project_id)
        db.add(cfg)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            cfg = db.query(TrackingConfig).filter(TrackingConfig.project_id == project_id).first()
        db.refresh(cfg)
    return cfg


def _serialize_cfg(cfg: TrackingConfig) -> dict:
    try:
        domains = json.loads(cfg.domains or "[]")
    except Exception:
        domains = []
    return {
        "id": cfg.id,
        "project_id": cfg.project_id,
        "collect_type": cfg.collect_type,
        "log_tag": cfg.log_tag,
        "batch_rule": cfg.batch_rule,
        "domains": domains,
        "dedup_window": cfg.dedup_window,
        "status": cfg.status,
        "started_at": cfg.started_at.strftime("%Y-%m-%d %H:%M:%S") if cfg.started_at else None,
        "updated_at": cfg.updated_at.strftime("%Y-%m-%d %H:%M:%S") if cfg.updated_at else None,
    }


# ---------------- 清单 CRUD ----------------

@router.get("/events", response_model=list[TrackingEventOut])
def list_events(project_id: int, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    return (
        db.query(TrackingEvent)
        .filter(TrackingEvent.project_id == project_id)
        .order_by(TrackingEvent.event_id.asc())
        .all()
    )


@router.post("/events", response_model=TrackingEventOut, status_code=201)
def create_event(payload: TrackingEventCreate, db: Session = Depends(get_db)):
    _get_project(payload.project_id, db)
    if not payload.event_id.strip():
        raise HTTPException(status_code=422, detail="事件ID不能为空")
    exists = (
        db.query(TrackingEvent)
        .filter(TrackingEvent.project_id == payload.project_id, TrackingEvent.event_id == payload.event_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail=f"事件ID「{payload.event_id}」已存在")
    rec = TrackingEvent(**payload.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.patch("/events/{event_id}", response_model=TrackingEventOut)
def update_event(event_id: int, payload: TrackingEventUpdate, db: Session = Depends(get_db)):
    rec = db.get(TrackingEvent, event_id)
    if not rec:
        raise HTTPException(status_code=404, detail="埋点不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    rec = db.get(TrackingEvent, event_id)
    if not rec:
        raise HTTPException(status_code=404, detail="埋点不存在")
    db.delete(rec)
    db.commit()


@router.post("/events/ignore")
def ignore_events(payload: TrackingIgnoreIn, db: Session = Depends(get_db)):
    """批量忽略/恢复埋点（清单级忽略，不参与监控匹配）。"""
    _get_project(payload.project_id, db)
    if not payload.ids:
        raise HTTPException(status_code=400, detail="请选择要忽略的事件")
    db.query(TrackingEvent).filter(
        TrackingEvent.project_id == payload.project_id,
        TrackingEvent.id.in_(payload.ids),
    ).update({"is_ignored": 1 if payload.ignored else 0}, synchronize_session=False)
    db.commit()
    return {"ok": True, "count": len(payload.ids), "ignored": payload.ignored}


@router.delete("/events", status_code=204)
def clear_events(project_id: int, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    db.query(TrackingEvent).filter(TrackingEvent.project_id == project_id).delete()
    db.commit()


@router.post("/events/reset", status_code=200)
def reset_counts(project_id: int, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    db.query(TrackingEvent).filter(TrackingEvent.project_id == project_id).update(
        {"trigger_count": 0, "last_triggered_at": None}
    )
    db.commit()
    return {"ok": True, "reset": True}


# ---------------- CSV 导入 / 导出 / 模板 ----------------

CSV_FIELDS = ["事件ID(事件名称)", "触发操作/打点含义"]


@router.post("/import")
async def import_csv(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _get_project(project_id, db)
    raw = await file.read()
    # 自动识别编码：UTF-8(带/不带BOM) 优先，GBK/GB18030 兜底（兼容 Excel 导出的 ANSI 中文 CSV）
    text = None
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        text = raw.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    errors: list[str] = []
    imported = 0
    duplicated = 0
    seen: set[str] = set()
    existing = {
        e.event_id
        for e in db.query(TrackingEvent).filter(TrackingEvent.project_id == project_id).all()
    }
    rows = list(reader)
    for i, row in enumerate(rows, start=2):  # 从第2行（数据行）计
        row = [c.strip() for c in row]
        if not any(row):
            continue
        if len(row) < 1 or not row[0]:
            errors.append(f"第{i}行：事件ID为空")
            continue
        eid = row[0]
        if eid in seen or eid in existing:
            duplicated += 1
            continue
        seen.add(eid)
        # 兼容两列：事件ID即事件名称；触发操作与打点含义同一列
        if len(row) >= 4 and row[1]:
            name, op, meaning = row[1], row[2], row[3]
        else:
            op = row[1] if len(row) > 1 else ""
            name, meaning = row[0], op
        rec = TrackingEvent(
            project_id=project_id,
            event_id=eid,
            event_name=name,
            operation=op,
            meaning=meaning,
        )
        db.add(rec)
        imported += 1
    db.commit()
    return {"imported": imported, "duplicated": duplicated, "errors": errors[:20]}


@router.get("/template")
def download_template():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_FIELDS)
    writer.writerow(["ad_load_failed_x", "进入广告位后广告加载失败时上报"])
    writer.writerow(["ad_click_x", "用户点击广告时上报"])
    content = buf.getvalue()
    return Response(
        content="\ufeff" + content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=tracking_template.csv"},
    )


@router.get("/export")
def export_csv(project_id: int, db: Session = Depends(get_db)):
    proj = _get_project(project_id, db)
    events = (
        db.query(TrackingEvent)
        .filter(TrackingEvent.project_id == project_id)
        .order_by(TrackingEvent.event_id.asc())
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["事件ID(事件名称)", "触发操作/打点含义", "触发次数", "触发状态", "最后触发时间"])
    for e in events:
        writer.writerow([
            e.event_id,
            e.operation or e.meaning,
            e.trigger_count,
            "已触发" if e.trigger_count > 0 else "未触发",
            e.last_triggered_at.strftime("%Y-%m-%d %H:%M:%S") if e.last_triggered_at else "",
        ])
    filename = f"{proj.name}_埋点结果_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    from urllib.parse import quote
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# ---------------- 采集配置 ----------------

@router.get("/config", response_model=TrackingConfigOut)
def get_config(project_id: int, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    return _get_config(project_id, db)


@router.put("/config", response_model=TrackingConfigOut)
def save_config(project_id: int, payload: TrackingConfigIn, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    cfg = _get_config(project_id, db)
    if collector_manager.is_running() and collector_manager.current_project() == project_id:
        raise HTTPException(status_code=400, detail="请先停止采集再修改配置")
    cfg.collect_type = payload.collect_type
    cfg.log_tag = payload.log_tag
    cfg.batch_rule = payload.batch_rule
    cfg.domains = json.dumps(payload.domains, ensure_ascii=False)
    cfg.dedup_window = payload.dedup_window
    db.commit()
    db.refresh(cfg)
    return cfg


@router.get("/status")
def status(project_id: int, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    cfg = _get_config(project_id, db)
    running = collector_manager.is_running() and collector_manager.current_project() == project_id
    return {
        "project_id": project_id,
        "status": "running" if running else "stopped",
        "collect_type": cfg.collect_type,
        "log_tag": cfg.log_tag,
        "dedup_window": cfg.dedup_window,
        "serial": collector_manager.current_serial() if running else "",
    }


# ---------------- 采集启停 ----------------

@router.post("/start")
def start(project_id: int, serial: str = "", db: Session = Depends(get_db)):
    _get_project(project_id, db)
    cfg = _get_config(project_id, db)
    if collector_manager.is_running():
        if collector_manager.current_project() == project_id:
            return {"ok": True, "status": "already_running", "serial": collector_manager.current_serial()}
        collector_manager.stop()  # 切换到新项目前先停旧的
    # 设备校验：指定设备必须在线；未指定时单设备自动选用，多设备提示选择
    dev = _list_online_devices()
    if serial:
        if serial not in dev:
            raise HTTPException(status_code=400, detail=f"设备 {serial} 未连接")
    elif len(dev) == 0:
        raise HTTPException(status_code=400, detail="无已连接设备，请先连接设备")
    elif len(dev) > 1:
        raise HTTPException(status_code=400, detail="检测到多台设备，请选择要监控的设备")
    else:
        serial = dev[0]
    config = {
        "collect_type": cfg.collect_type,
        "log_tag": cfg.log_tag,
        "dedup_window": cfg.dedup_window,
    }
    collector_manager.start(project_id, config, serial)
    cfg.status = "running"
    cfg.started_at = datetime.now()
    db.commit()
    return {"ok": True, "status": "running", "serial": serial}


def _list_online_devices() -> list[str]:
    """返回当前所有 state=device 的 adb 设备 serial 列表。"""
    import subprocess
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True, timeout=8,
            encoding="utf-8", errors="replace",
        )
    except Exception:
        return []
    out = []
    for ln in result.stdout.splitlines()[1:]:
        parts = ln.split()
        if len(parts) >= 2 and parts[1] == "device":
            out.append(parts[0])
    return out


@router.post("/stop")
def stop(project_id: int, db: Session = Depends(get_db)):
    collector_manager.stop()
    cfg = _get_config(project_id, db)
    cfg.status = "stopped"
    db.commit()
    return {"ok": True, "status": "stopped"}


# ---------------- WebSocket 实时推送（独立挂载，使用会话鉴权） ----------------

ws_router = APIRouter(prefix="/ws", tags=["tracking-ws"], dependencies=[Depends(get_current_websocket_user)])


@router.post("/simulate")
def simulate_event(project_id: int, eid: str, db: Session = Depends(get_db)):
    """模拟上报一次事件（联调/验证配置用）：走真实匹配、去重、计数与 WS 推送链路。"""
    import time
    _get_project(project_id, db)
    cfg = _get_config(project_id, db)
    events = {
        e.event_id: e.id
        for e in db.query(TrackingEvent).filter(TrackingEvent.project_id == project_id).all()
    }
    now = int(time.time())
    collector_manager._handle_event(
        project_id, {"eid": eid, "ts": now * 1000}, events, {}, int(cfg.dedup_window or 3)
    )
    return {"ok": True, "eid": eid}


@router.get("/adb/devices")
def adb_devices():
    """查询 ADB 可用性与已连接设备（adb devices -l 解析）。"""
    import subprocess
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {"adb_installed": False, "devices": [], "error": "未检测到 adb，请安装 Android SDK platform-tools"}
    except Exception as e:  # noqa: BLE001
        return {"adb_installed": True, "devices": [], "error": str(e)}
    devices = []
    for ln in result.stdout.splitlines()[1:]:
        parts = ln.split()
        if len(parts) >= 2:
            model = ""
            for p in parts[2:]:
                if p.startswith("model:"):
                    model = p.split(":", 1)[1]
                    break
            devices.append({"serial": parts[0], "state": parts[1], "model": model})
    return {"adb_installed": True, "devices": devices, "error": ""}


@ws_router.websocket("/tracking")
async def tracking_ws(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
