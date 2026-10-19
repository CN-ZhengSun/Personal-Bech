from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TestCaseStepCreate(BaseModel):
    step_no: int = 1
    action: str = ""
    expected: str = ""


class TestCaseStepOut(ORMModel):
    id: int
    case_id: int
    step_no: int
    action: str
    expected: str


class TestCaseCreate(BaseModel):
    project_id: int
    module: str | None = None
    title: str
    preconditions: str = ""
    expected: str = ""
    priority: str = "P1"
    case_type: str = "functional"
    tags: str | None = None
    status: str = "active"
    environment: str | None = None
    version: str | None = None
    steps: list[TestCaseStepCreate] = []
    requirement_ids: list[int] = []


class TestCaseUpdate(BaseModel):
    module: str | None = None
    title: str | None = None
    preconditions: str | None = None
    expected: str | None = None
    priority: str | None = None
    case_type: str | None = None
    tags: str | None = None
    status: str | None = None
    environment: str | None = None
    version: str | None = None
    steps: list[TestCaseStepCreate] | None = None


class TestCaseOut(ORMModel):
    id: int
    project_id: int
    module: str | None
    title: str
    preconditions: str
    expected: str | None = None
    priority: str
    case_type: str
    tags: str | None
    status: str
    environment: str | None
    version: str | None
    created_at: datetime
    updated_at: datetime


class CaseDetailOut(TestCaseOut):
    steps: list[TestCaseStepOut] = []
    requirement_ids: list[int] = []
