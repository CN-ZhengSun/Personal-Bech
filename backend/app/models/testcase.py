from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TestCase(Base):
    __tablename__ = "test_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    preconditions: Mapped[str] = mapped_column(Text, default="")
    expected: Mapped[str] = mapped_column(Text, default="")  # 最终预期结果
    # P0 / P1 / P2 / P3
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    # functional / ui / api / performance / other
    case_type: Mapped[str] = mapped_column(String(20), default="functional")
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # active / deprecated
    status: Mapped[str] = mapped_column(String(20), default="active")
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TestCaseStep(Base):
    __tablename__ = "test_case_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_case.id"), index=True)
    step_no: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(Text, default="")
    expected: Mapped[str] = mapped_column(Text, default="")


class CaseRequirement(Base):
    """用例-需求关联（追踪矩阵）。"""

    __tablename__ = "case_requirement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_case.id"), index=True)
    requirement_id: Mapped[int] = mapped_column(Integer, ForeignKey("requirement.id"), index=True)
