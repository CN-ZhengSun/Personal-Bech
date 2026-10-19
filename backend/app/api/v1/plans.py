from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.plan import TestPlan
from app.schemas.plan import TestPlanCreate, TestPlanOut, TestPlanUpdate

router = APIRouter(prefix="/plans", tags=["plans"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[TestPlanOut])
def list_plans(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(TestPlan)
    if project_id:
        q = q.filter(TestPlan.project_id == project_id)
    return q.order_by(TestPlan.id.desc()).all()


@router.post("", response_model=TestPlanOut, status_code=201)
def create_plan(payload: TestPlanCreate, db: Session = Depends(get_db)):
    plan = TestPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=TestPlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(TestPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="测试计划不存在")
    return plan


@router.patch("/{plan_id}", response_model=TestPlanOut)
def update_plan(plan_id: int, payload: TestPlanUpdate, db: Session = Depends(get_db)):
    plan = db.get(TestPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="测试计划不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(TestPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="测试计划不存在")
    db.delete(plan)
    db.commit()


@router.get("/{plan_id}/progress")
def plan_progress(plan_id: int, db: Session = Depends(get_db)):
    """计划执行进度统计。"""
    from app.models.execution import TestExecution

    execs = db.query(TestExecution).filter(TestExecution.plan_id == plan_id).all()
    total = len(execs)
    counts = {"pass": 0, "fail": 0, "blocked": 0, "skipped": 0, "untested": 0}
    for e in execs:
        counts[e.status] = counts.get(e.status, 0) + 1
    return {"plan_id": plan_id, "total": total, "counts": counts,
            "pass_rate": round(counts["pass"] / total * 100, 1) if total else 0}
