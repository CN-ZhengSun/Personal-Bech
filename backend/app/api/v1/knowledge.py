from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.upload import UPLOAD_DIR
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.knowledge import KnowledgeDoc
from app.schemas.knowledge import KnowledgeDocCreate, KnowledgeDocOut, KnowledgeDocUpdate
from app.services.knowledge_extract import extract_file_text

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(get_current_user)])


def _build_search_text(doc: KnowledgeDoc) -> str:
    """构建全文检索文本：标题 + 分类 + 标签 + 内容 + 文件提取文本。"""
    parts = [doc.title or "", doc.category or "", doc.tags or "", doc.content or ""]
    if doc.file_url and doc.file_type:
        fpath = (UPLOAD_DIR / doc.file_url.removeprefix("/uploads/")).resolve()
        # 仅允许读取 uploads 目录内的文件
        if str(fpath).startswith(str(UPLOAD_DIR.resolve())):
            parts.append(extract_file_text(fpath, doc.file_type))
    return "\n".join(parts)


@router.get("", response_model=list[KnowledgeDocOut])
def list_docs(q: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    """知识库列表/搜索。q 匹配标题、标签、分类及文件内容（提取文本）。"""
    query = db.query(KnowledgeDoc)
    if q and q.strip():
        kw = f"%{q.strip()}%"
        query = query.filter(or_(KnowledgeDoc.search_text.like(kw), KnowledgeDoc.title.like(kw)))
    if category:
        query = query.filter(KnowledgeDoc.category == category)
    return query.order_by(KnowledgeDoc.id.desc()).all()


@router.post("", response_model=KnowledgeDocOut, status_code=201)
def create_doc(payload: KnowledgeDocCreate, db: Session = Depends(get_db)):
    doc = KnowledgeDoc(**payload.model_dump())
    doc.search_text = _build_search_text(doc)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doc_id}", response_model=KnowledgeDocOut)
def get_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(KnowledgeDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.patch("/{doc_id}", response_model=KnowledgeDocOut)
def update_doc(doc_id: int, payload: KnowledgeDocUpdate, db: Session = Depends(get_db)):
    doc = db.get(KnowledgeDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(doc, k, v)
    doc.search_text = _build_search_text(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(KnowledgeDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 删除关联文件（仅限 uploads 目录内，防路径穿越）
    if doc.file_url:
        rel = doc.file_url.removeprefix("/uploads/")
        fpath = (UPLOAD_DIR / rel).resolve()
        if str(fpath).startswith(str(UPLOAD_DIR.resolve())) and fpath.exists():
            try:
                fpath.unlink()
            except OSError:
                pass
    db.delete(doc)
    db.commit()
