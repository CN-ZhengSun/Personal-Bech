from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.automation import AutomationScript, AutomationTask
from app.schemas.automation import (
    AutomationScriptCreate,
    AutomationScriptOut,
    AutomationScriptUpdate,
    AutomationTaskCreate,
    AutomationTaskOut,
    AutomationTaskUpdate,
)

router = APIRouter(prefix="/automation", tags=["automation"], dependencies=[Depends(get_current_user)])

# ---------------- 脚本 ----------------

script_router = APIRouter(prefix="/scripts", tags=["automation-scripts"], dependencies=[Depends(get_current_user)])


@script_router.get("", response_model=list[AutomationScriptOut])
def list_scripts(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(AutomationScript)
    if project_id:
        q = q.filter(AutomationScript.project_id == project_id)
    return q.order_by(AutomationScript.id.desc()).all()


@script_router.post("", response_model=AutomationScriptOut, status_code=201)
def create_script(payload: AutomationScriptCreate, db: Session = Depends(get_db)):
    scr = AutomationScript(**payload.model_dump())
    db.add(scr)
    db.commit()
    db.refresh(scr)
    return scr


@script_router.patch("/{script_id}", response_model=AutomationScriptOut)
def update_script(script_id: int, payload: AutomationScriptUpdate, db: Session = Depends(get_db)):
    scr = db.get(AutomationScript, script_id)
    if not scr:
        raise HTTPException(status_code=404, detail="脚本不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(scr, k, v)
    db.commit()
    db.refresh(scr)
    return scr


@script_router.delete("/{script_id}", status_code=204)
def delete_script(script_id: int, db: Session = Depends(get_db)):
    scr = db.get(AutomationScript, script_id)
    if not scr:
        raise HTTPException(status_code=404, detail="脚本不存在")
    db.query(AutomationTask).filter(AutomationTask.script_id == script_id).delete()
    db.delete(scr)
    db.commit()


# ---------------- 任务 ----------------

task_router = APIRouter(prefix="/tasks", tags=["automation-tasks"], dependencies=[Depends(get_current_user)])


@task_router.get("", response_model=list[AutomationTaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(AutomationTask).order_by(AutomationTask.id.desc()).all()


@task_router.post("", response_model=AutomationTaskOut, status_code=201)
def create_task(payload: AutomationTaskCreate, db: Session = Depends(get_db)):
    t = AutomationTask(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@task_router.patch("/{task_id}", response_model=AutomationTaskOut)
def update_task(task_id: int, payload: AutomationTaskUpdate, db: Session = Depends(get_db)):
    t = db.get(AutomationTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@task_router.post("/{task_id}/run", response_model=AutomationTaskOut)
def run_task(task_id: int, db: Session = Depends(get_db)):
    """模拟触发执行：记录运行时间与报告（真实执行引擎后期接入）。"""
    t = db.get(AutomationTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    t.last_run_at = datetime.now()
    t.report = f"[{datetime.now():%Y-%m-%d %H:%M}] 执行完成：脚本 #{t.script_id}，结果待接入执行引擎。"
    db.commit()
    db.refresh(t)
    return t


@task_router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.get(AutomationTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(t)
    db.commit()


router.include_router(script_router)
router.include_router(task_router)
