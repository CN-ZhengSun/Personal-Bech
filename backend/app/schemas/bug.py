from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class BugCreate(BaseModel):
    project_id: int
    requirement_id: int | None = None
    case_id: int | None = None
    title: str
    description: str = ""
    steps: str = ""
    severity: str = "major"
    priority: str = "P1"
    probability: str = "always"
    status: str = "to_fix"
    module: str | None = None
    version: str | None = None
    environment: str | None = None
    assignee: str | None = None
    reporter: str | None = None
    attachments: str = ""


class BugUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    steps: str | None = None
    severity: str | None = None
    priority: str | None = None
    probability: str | None = None
    status: str | None = None
    module: str | None = None
    version: str | None = None
    environment: str | None = None
    assignee: str | None = None
    attachments: str | None = None


class BugOut(ORMModel):
    id: int
    project_id: int
    requirement_id: int | None
    case_id: int | None
    title: str
    description: str
    steps: str
    severity: str
    priority: str
    probability: str
    status: str
    module: str | None
    version: str | None
    environment: str | None
    assignee: str | None
    reporter: str | None
    attachments: str
    created_at: datetime
    updated_at: datetime


class BugCommentCreate(BaseModel):
    user: str | None = None
    event_type: str | None = None
    content: str


class BugCommentOut(ORMModel):
    id: int
    bug_id: int
    user: str | None
    event_type: str
    content: str
    created_at: datetime
