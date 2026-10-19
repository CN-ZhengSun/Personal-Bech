from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.prd import PrdDocument, Requirement
from app.models.testcase import CaseRequirement
from app.schemas.prd import (
    PrdDocumentCreate,
    PrdDocumentOut,
    RequirementCreate,
    RequirementOut,
    RequirementUpdate,
)

router = APIRouter(prefix="/requirements", tags=["requirements"], dependencies=[Depends(get_current_user)])

# ---------------- PRD 文档 ----------------

prd_router = APIRouter(prefix="/prd", tags=["prd"], dependencies=[Depends(get_current_user)])


@prd_router.get("", response_model=list[PrdDocumentOut])
def list_prd(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(PrdDocument)
    if project_id:
        q = q.filter(PrdDocument.project_id == project_id)
    return q.order_by(PrdDocument.id.desc()).all()


@prd_router.post("", response_model=PrdDocumentOut, status_code=201)
def create_prd(payload: PrdDocumentCreate, db: Session = Depends(get_db)):
    doc = PrdDocument(**payload.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@prd_router.get("/{prd_id}", response_model=PrdDocumentOut)
def get_prd(prd_id: int, db: Session = Depends(get_db)):
    doc = db.get(PrdDocument, prd_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PRD 不存在")
    return doc


@prd_router.delete("/{prd_id}", status_code=204)
def delete_prd(prd_id: int, db: Session = Depends(get_db)):
    doc = db.get(PrdDocument, prd_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PRD 不存在")
    db.delete(doc)
    db.commit()


# ---------------- 需求点 ----------------

@router.get("", response_model=list[RequirementOut])
def list_requirements(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Requirement)
    if project_id:
        q = q.filter(Requirement.project_id == project_id)
    return q.order_by(Requirement.id.desc()).all()


@router.post("", response_model=RequirementOut, status_code=201)
def create_requirement(payload: RequirementCreate, db: Session = Depends(get_db)):
    req = Requirement(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/{req_id}", response_model=RequirementOut)
def get_requirement(req_id: int, db: Session = Depends(get_db)):
    req = db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    return req


@router.patch("/{req_id}", response_model=RequirementOut)
def update_requirement(req_id: int, payload: RequirementUpdate, db: Session = Depends(get_db)):
    req = db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(req, k, v)
    db.commit()
    db.refresh(req)
    return req


@router.delete("/{req_id}", status_code=204)
def delete_requirement(req_id: int, db: Session = Depends(get_db)):
    req = db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    db.query(CaseRequirement).filter(CaseRequirement.requirement_id == req_id).delete()
    db.delete(req)
    db.commit()


@router.get("/{req_id}/coverage")
def requirement_coverage(req_id: int, db: Session = Depends(get_db)):
    """需求覆盖统计：关联用例数、缺陷数。"""
    from app.models.bug import Bug

    case_count = (
        db.query(CaseRequirement).filter(CaseRequirement.requirement_id == req_id).count()
    )
    bug_count = db.query(Bug).filter(Bug.requirement_id == req_id).count()
    return {"requirement_id": req_id, "case_count": case_count, "bug_count": bug_count}
