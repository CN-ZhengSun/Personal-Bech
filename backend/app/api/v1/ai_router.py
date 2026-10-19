from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai import ModelConfig, PromptTemplate, Skill
from app.schemas.ai import (
    ModelConfigCreate,
    ModelConfigOut,
    ModelConfigUpdate,
    PromptTemplateCreate,
    PromptTemplateOut,
    SkillCreate,
    SkillOut,
    SkillUpdate,
)

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(get_current_user)])

# ---------------- 模型配置 ----------------

model_router = APIRouter(prefix="/models", tags=["ai-models"], dependencies=[Depends(get_current_user)])


@model_router.get("", response_model=list[ModelConfigOut])
def list_models(db: Session = Depends(get_db)):
    return db.query(ModelConfig).order_by(ModelConfig.id).all()


@model_router.post("", response_model=ModelConfigOut, status_code=201)
def create_model(payload: ModelConfigCreate, db: Session = Depends(get_db)):
    m = ModelConfig(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@model_router.patch("/{model_id}", response_model=ModelConfigOut)
def update_model(model_id: int, payload: ModelConfigUpdate, db: Session = Depends(get_db)):
    m = db.get(ModelConfig, model_id)
    if not m:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@model_router.delete("/{model_id}", status_code=204)
def delete_model(model_id: int, db: Session = Depends(get_db)):
    m = db.get(ModelConfig, model_id)
    if not m:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    db.delete(m)
    db.commit()


# ---------------- Skill 编排 ----------------

skill_router = APIRouter(prefix="/skills", tags=["ai-skills"], dependencies=[Depends(get_current_user)])


@skill_router.get("", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    return db.query(Skill).order_by(Skill.id.desc()).all()


@skill_router.post("", response_model=SkillOut, status_code=201)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)):
    s = Skill(**payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@skill_router.patch("/{skill_id}", response_model=SkillOut)
def update_skill(skill_id: int, payload: SkillUpdate, db: Session = Depends(get_db)):
    s = db.get(Skill, skill_id)
    if not s:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@skill_router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    s = db.get(Skill, skill_id)
    if not s:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    db.delete(s)
    db.commit()


# ---------------- Prompt 模板 ----------------

prompt_router = APIRouter(prefix="/prompts", tags=["ai-prompts"], dependencies=[Depends(get_current_user)])


@prompt_router.get("", response_model=list[PromptTemplateOut])
def list_prompts(db: Session = Depends(get_db)):
    return db.query(PromptTemplate).order_by(PromptTemplate.id.desc()).all()


@prompt_router.post("", response_model=PromptTemplateOut, status_code=201)
def create_prompt(payload: PromptTemplateCreate, db: Session = Depends(get_db)):
    p = PromptTemplate(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@prompt_router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    p = db.get(PromptTemplate, prompt_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prompt 不存在")
    db.delete(p)
    db.commit()


router.include_router(model_router)
router.include_router(skill_router)
router.include_router(prompt_router)
