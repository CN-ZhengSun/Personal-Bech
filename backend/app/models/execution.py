from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TestExecution(Base):
    """用例执行记录。"""

    __tablename__ = "test_execution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("test_plan.id"), nullable=True, index=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_case.id"), index=True)
    assignee: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # untested / pass / fail / blocked / skipped
    status: Mapped[str] = mapped_column(String(20), default="untested")
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actual_result: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")  # 截图/日志路径
    fail_reason: Mapped[str] = mapped_column(Text, default="")
    bug_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
