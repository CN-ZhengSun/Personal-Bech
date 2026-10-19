from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.execution import TestExecution
from app.models.testcase import TestCase
from app.schemas.execution import (
    BatchExecuteCreate,
    TestExecutionCreate,
    TestExecutionOut,
    TestExecutionUpdate,
)

router = APIRouter(prefix="/executions", tags=["executions"], dependencies=[Depends(get_current_user)])

VALID_STATUSES = ("untested", "pass", "fail", "blocked", "skipped")


def _can_modify(user, rec: TestExecution) -> bool:
    """执行人与管理员可修改执行记录；未指派时允许执行人首次认领。"""
    if user.role == "admin":
        return True
    if not rec.assignee:
        return True
    return rec.assignee == user.username


@router.get("", response_model=list[TestExecutionOut])
def list_executions(plan_id: int | None = None, case_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(TestExecution)
    if plan_id:
        q = q.filter(TestExecution.plan_id == plan_id)
    if case_id:
        q = q.filter(TestExecution.case_id == case_id)
    return q.order_by(TestExecution.id.desc()).limit(500).all()


@router.post("", response_model=TestExecutionOut, status_code=201)
def create_execution(payload: TestExecutionCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="非法状态值")
    # 环境/版本与用例保持一致（执行未单独指定时继承用例）
    case = db.get(TestCase, payload.case_id)
    if case:
        if not data.get("environment") and case.environment:
            data["environment"] = case.environment
        if not data.get("version") and case.version:
            data["version"] = case.version
    if payload.status in ("pass", "fail", "blocked", "skipped"):
        data["executed_at"] = datetime.now()
    rec = TestExecution(**data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/batch", response_model=list[TestExecutionOut], status_code=201)
def batch_create(payload: BatchExecuteCreate, db: Session = Depends(get_db)):
    recs = []
    cases = {c.id: c for c in db.query(TestCase).filter(TestCase.id.in_(payload.case_ids)).all()}
    for cid in payload.case_ids:
        c = cases.get(cid)
        rec = TestExecution(
            plan_id=payload.plan_id,
            case_id=cid,
            assignee=payload.assignee,
            status="untested",
            environment=payload.environment or (c.environment if c else None),
            version=payload.version or (c.version if c else None),
        )
        db.add(rec)
        recs.append(rec)
    db.commit()
    for r in recs:
        db.refresh(r)
    return recs


@router.patch("/{exec_id}", response_model=TestExecutionOut)
def update_execution(exec_id: int, payload: TestExecutionUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    rec = db.get(TestExecution, exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if not _can_modify(user, rec):
        raise HTTPException(status_code=403, detail="仅该用例执行人和管理员可修改")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail="非法状态值")
        if data["status"] in ("pass", "fail", "blocked", "skipped"):
            rec.executed_at = datetime.now()
            # 修改状态时自动补齐执行人（若尚未指派）
            if not rec.assignee:
                data["assignee"] = user.username
    for k, v in data.items():
        setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/{exec_id}", status_code=204)
def delete_execution(exec_id: int, db: Session = Depends(get_db)):
    rec = db.get(TestExecution, exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    db.delete(rec)
    db.commit()
