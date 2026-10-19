from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PrdDocument(Base):
    """PRD 文档（富文本/Markdown，支持多版本）。"""

    __tablename__ = "prd_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    owner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attachment: Mapped[str] = mapped_column(Text, default="")  # 附件文件名（展示用）
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Requirement(Base):
    """需求点（从 PRD 拆分的可验收需求，关联用例与缺陷）。"""

    __tablename__ = "requirement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    prd_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("prd_document.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # P0 / P1 / P2
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # draft / review / approved / changed / done
    status: Mapped[str] = mapped_column(String(20), default="draft")
    acceptance: Mapped[str] = mapped_column(Text, default="")
    target_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 期望上线时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
