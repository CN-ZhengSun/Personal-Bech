from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Bug(Base):
    __tablename__ = "bug"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    requirement_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("requirement.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("test_case.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[str] = mapped_column(Text, default="")
    # critical / major / minor / trivial
    severity: Mapped[str] = mapped_column(String(20), default="major")
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    # always / occasional / multiple / unreproducible
    probability: Mapped[str] = mapped_column(String(20), default="always")
    # to_fix / fixing / fixed / verified / cant_fix / wont_fix / by_design / reopen
    status: Mapped[str] = mapped_column(String(20), default="to_fix")
    module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reporter: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attachments: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BugComment(Base):
    """缺陷流转记录/评论。event_type: created(创建) / status(状态变更) / comment(评论)。"""

    __tablename__ = "bug_comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bug_id: Mapped[int] = mapped_column(Integer, ForeignKey("bug.id"), index=True)
    user: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), default="comment")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
