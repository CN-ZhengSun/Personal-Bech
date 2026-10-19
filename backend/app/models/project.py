from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Project(Base):
    """项目空间（MVP 首个核心实体，作为骨架示例）。"""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # draft / researching / approved / delivering / delivered
    status: Mapped[str] = mapped_column(String(20), default="draft")
    deliver_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
