from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TrackingEventCreate(BaseModel):
    project_id: int
    event_id: str
    event_name: str = ""
    operation: str = ""
    meaning: str = ""


class TrackingEventUpdate(BaseModel):
    event_id: str | None = None
    event_name: str | None = None
    operation: str | None = None
    meaning: str | None = None


class TrackingEventOut(ORMModel):
    id: int
    project_id: int
    event_id: str
    event_name: str
    operation: str
    meaning: str
    is_ignored: int
    trigger_count: int
    last_triggered_at: datetime | None
    created_at: datetime


class TrackingIgnoreIn(BaseModel):
    project_id: int
    ids: list[int]
    ignored: bool = True


class TrackingConfigIn(BaseModel):
    collect_type: str = "adb"
    log_tag: str = "hk3"
    batch_rule: str = ""
    domains: list[str] = []
    dedup_window: int = 3


class TrackingConfigOut(ORMModel):
    id: int
    project_id: int
    collect_type: str
    log_tag: str
    batch_rule: str
    domains: str
    dedup_window: int
    status: str
    started_at: datetime | None
    updated_at: datetime
