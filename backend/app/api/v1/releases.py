from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.release import Environment, Version
from app.schemas.release import EnvironmentCreate, EnvironmentOut, VersionCreate, VersionOut

router = APIRouter(prefix="/releases", tags=["releases"], dependencies=[Depends(get_current_user)])

# ---------------- 版本 ----------------

version_router = APIRouter(prefix="/versions", tags=["versions"], dependencies=[Depends(get_current_user)])


@version_router.get("", response_model=list[VersionOut])
def list_versions(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Version)
    if project_id:
        q = q.filter(Version.project_id == project_id)
    return q.order_by(Version.id.desc()).all()


@version_router.post("", response_model=VersionOut, status_code=201)
def create_version(payload: VersionCreate, db: Session = Depends(get_db)):
    v = Version(**payload.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@version_router.patch("/{version_id}", response_model=VersionOut)
def update_version(version_id: int, payload: VersionCreate, db: Session = Depends(get_db)):
    v = db.get(Version, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    for k, val in payload.model_dump(exclude_none=True).items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return v


@version_router.delete("/{version_id}", status_code=204)
def delete_version(version_id: int, db: Session = Depends(get_db)):
    v = db.get(Version, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    db.delete(v)
    db.commit()


# ---------------- 环境 ----------------

env_router = APIRouter(prefix="/environments", tags=["environments"], dependencies=[Depends(get_current_user)])


@env_router.get("", response_model=list[EnvironmentOut])
def list_environments(db: Session = Depends(get_db)):
    return db.query(Environment).order_by(Environment.id).all()


@env_router.post("", response_model=EnvironmentOut, status_code=201)
def create_environment(payload: EnvironmentCreate, db: Session = Depends(get_db)):
    env = Environment(**payload.model_dump())
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


@env_router.patch("/{env_id}", response_model=EnvironmentOut)
def update_environment(env_id: int, payload: EnvironmentCreate, db: Session = Depends(get_db)):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    for k, val in payload.model_dump(exclude_none=True).items():
        setattr(env, k, val)
    db.commit()
    db.refresh(env)
    return env


@env_router.delete("/{env_id}", status_code=204)
def delete_environment(env_id: int, db: Session = Depends(get_db)):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    db.delete(env)
    db.commit()


router.include_router(version_router)
router.include_router(env_router)
