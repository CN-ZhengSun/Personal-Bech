from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AutomationScript(Base):
    """自动化脚本（UI/API），脚本托管。"""

    __tablename__ = "automation_script"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("test_case.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # ui / api
    script_type: Mapped[str] = mapped_column(String(10), default="ui")
    framework: Mapped[str | None] = mapped_column(String(50), nullable=True)  # pytest/selenium/playwright
    language: Mapped[str | None] = mapped_column(String(20), default="python")
    repo_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # active / deprecated
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AutomationTask(Base):
    """自动化调度任务。"""

    __tablename__ = "automation_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    script_id: Mapped[int] = mapped_column(Integer, ForeignKey("automation_script.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # cron 表达式，如 0 2 * * *；空 = 手动
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # enabled / disabled
    status: Mapped[str] = mapped_column(String(20), default="enabled")
    report: Mapped[str] = mapped_column(Text, default="")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
