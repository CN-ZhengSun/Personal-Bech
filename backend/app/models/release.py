from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Version(Base):
    """被测版本。"""

    __tablename__ = "version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # dev / testing / released / archived
    status: Mapped[str] = mapped_column(String(20), default="testing")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Environment(Base):
    """测试环境。"""

    __tablename__ = "environment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    base_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # available / maintenance / offline
    status: Mapped[str] = mapped_column(String(20), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
