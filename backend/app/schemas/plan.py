from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TestPlanCreate(BaseModel):
    project_id: int
    version_id: int | None = None
    name: str
    description: str = ""
    start_date: str | None = None
    end_date: str | None = None
    status: str = "draft"


class TestPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    version_id: int | None = None


class TestPlanOut(ORMModel):
    id: int
    project_id: int
    version_id: int | None
    name: str
    description: str
    start_date: str | None
    end_date: str | None
    status: str
    created_at: datetime
    updated_at: datetime
