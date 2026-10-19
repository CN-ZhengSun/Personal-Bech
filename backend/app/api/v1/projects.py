from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    name: str | None = None,
    owner: str | None = None,
    date_type: str | None = None,  # created / deliver
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Project)
    if name:
        q = q.filter(Project.name.like(f"%{name}%"))
    if owner:
        q = q.filter(Project.owner.like(f"%{owner}%"))
    if date_type == "created" and (start_date or end_date):
        col = func.date(Project.created_at)
        if start_date:
            q = q.filter(col >= start_date)
        if end_date:
            q = q.filter(col <= end_date)
    elif date_type == "deliver" and (start_date or end_date):
        col = func.date(Project.deliver_date)
        if start_date:
            q = q.filter(col >= start_date)
        if end_date:
            q = q.filter(col <= end_date)
    return q.order_by(Project.id.desc()).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    exists = db.query(Project).filter(Project.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="项目名称已存在")
    proj = Project(**payload.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    proj = db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return proj


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    proj = db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    data = payload.model_dump(exclude_none=True)
    if "name" in data:
        exists = db.query(Project).filter(Project.name == data["name"], Project.id != project_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="项目名称已存在")
    for k, v in data.items():
        setattr(proj, k, v)
    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    proj = db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    # 级联删除该项目全部关联数据（子表在前）
    case_ids = [
        r[0]
        for r in db.execute(text("SELECT id FROM test_case WHERE project_id=:p"), {"p": project_id})
    ]
    req_ids = [
        r[0]
        for r in db.execute(text("SELECT id FROM requirement WHERE project_id=:p"), {"p": project_id})
    ]
    db.execute(
        text("DELETE FROM automation_task WHERE script_id IN (SELECT id FROM automation_script WHERE project_id=:p)"),
        {"p": project_id},
    )
    db.execute(
        text("DELETE FROM bug_comment WHERE bug_id IN (SELECT id FROM bug WHERE project_id=:p)"),
        {"p": project_id},
    )
    if case_ids:
        placeholders = ",".join([":cid%d" % i for i in range(len(case_ids))])
        params = {"p": project_id, **{"cid%d" % i: c for i, c in enumerate(case_ids)}}
        db.execute(text(f"DELETE FROM test_execution WHERE case_id IN ({placeholders})"), params)
        db.execute(text(f"DELETE FROM case_requirement WHERE case_id IN ({placeholders})"), params)
        db.execute(text(f"DELETE FROM test_case_step WHERE case_id IN ({placeholders})"), params)
    if req_ids:
        placeholders = ",".join([":rid%d" % i for i in range(len(req_ids))])
        params = {"p": project_id, **{"rid%d" % i: c for i, c in enumerate(req_ids)}}
        db.execute(text(f"DELETE FROM case_requirement WHERE requirement_id IN ({placeholders})"), params)
    db.execute(text("DELETE FROM automation_script WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM bug WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM test_case WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM knowledge_doc WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM test_plan WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM version WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM requirement WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM prd_document WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM tracking_event WHERE project_id=:p"), {"p": project_id})
    db.execute(text("DELETE FROM tracking_config WHERE project_id=:p"), {"p": project_id})
    db.delete(proj)
    db.commit()
