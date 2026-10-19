from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PrdDocumentCreate(BaseModel):
    project_id: int
    title: str
    content: str = ""
    module: str | None = None
    version: str = "v1.0"
    owner: str | None = None
    attachment: str = ""


class PrdDocumentOut(ORMModel):
    id: int
    project_id: int
    title: str
    content: str
    module: str | None
    version: str
    owner: str | None
    attachment: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class RequirementCreate(BaseModel):
    project_id: int
    prd_id: int | None = None
    title: str
    description: str = ""
    priority: str = "P1"
    module: str | None = None
    owner: str | None = None
    status: str = "draft"
    acceptance: str = ""
    target_date: str | None = None


class RequirementUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    module: str | None = None
    owner: str | None = None
    status: str | None = None
    acceptance: str | None = None
    target_date: str | None = None


class RequirementOut(ORMModel):
    id: int
    project_id: int
    prd_id: int | None
    title: str
    description: str
    priority: str
    module: str | None
    owner: str | None
    status: str
    acceptance: str
    target_date: str | None
    created_at: datetime
    updated_at: datetime
