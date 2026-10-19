from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TestExecutionCreate(BaseModel):
    plan_id: int | None = None
    case_id: int
    assignee: str | None = None
    status: str = "untested"
    environment: str | None = None
    version: str | None = None
    actual_result: str = ""
    evidence: str = ""
    fail_reason: str = ""
    bug_id: int | None = None


class TestExecutionUpdate(BaseModel):
    status: str | None = None
    actual_result: str | None = None
    evidence: str | None = None
    fail_reason: str | None = None
    assignee: str | None = None
    environment: str | None = None
    version: str | None = None
    bug_id: int | None = None


class TestExecutionOut(ORMModel):
    id: int
    plan_id: int | None
    case_id: int
    assignee: str | None
    status: str
    environment: str | None
    version: str | None
    actual_result: str
    evidence: str
    fail_reason: str
    bug_id: int | None
    executed_at: datetime | None
    created_at: datetime


class BatchExecuteCreate(BaseModel):
    plan_id: int | None = None
    case_ids: list[int]
    assignee: str | None = None
    environment: str | None = None
    version: str | None = None
