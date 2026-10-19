from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class KnowledgeDocCreate(BaseModel):
    project_id: int | None = None
    category: str = "通用"
    title: str
    content: str = ""
    tags: str | None = None
    visibility: str = "global"
    file_url: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_type: str | None = None


class KnowledgeDocUpdate(BaseModel):
    category: str | None = None
    title: str | None = None
    content: str | None = None
    tags: str | None = None
    visibility: str | None = None
    file_url: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_type: str | None = None


class KnowledgeDocOut(ORMModel):
    id: int
    project_id: int | None
    category: str
    title: str
    content: str
    tags: str | None
    visibility: str
    file_url: str | None
    file_name: str | None
    file_size: int | None
    file_type: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
