from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class AutomationScriptCreate(BaseModel):
    project_id: int
    case_id: int | None = None
    name: str
    description: str = ""
    script_type: str = "ui"
    framework: str | None = None
    language: str = "python"
    repo_url: str | None = None
    content: str = ""
    version: str | None = None


class AutomationScriptUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    script_type: str | None = None
    framework: str | None = None
    content: str | None = None
    repo_url: str | None = None
    version: str | None = None
    status: str | None = None


class AutomationScriptOut(ORMModel):
    id: int
    project_id: int
    case_id: int | None
    name: str
    description: str
    script_type: str
    framework: str | None
    language: str
    repo_url: str | None
    content: str
    version: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class AutomationTaskCreate(BaseModel):
    script_id: int
    name: str
    schedule: str | None = None
    environment: str | None = None
    status: str = "enabled"


class AutomationTaskUpdate(BaseModel):
    name: str | None = None
    schedule: str | None = None
    environment: str | None = None
    status: str | None = None
    report: str | None = None


class AutomationTaskOut(ORMModel):
    id: int
    script_id: int
    name: str
    schedule: str | None
    environment: str | None
    status: str
    report: str
    last_run_at: datetime | None
    created_at: datetime
