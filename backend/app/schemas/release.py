from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class VersionCreate(BaseModel):
    project_id: int
    name: str
    description: str = ""
    status: str = "testing"


class VersionOut(ORMModel):
    id: int
    project_id: int
    name: str
    description: str
    status: str
    created_at: datetime


class EnvironmentCreate(BaseModel):
    name: str
    base_url: str | None = None
    description: str = ""
    status: str = "available"


class EnvironmentOut(ORMModel):
    id: int
    name: str
    base_url: str | None
    description: str
    status: str
    created_at: datetime
