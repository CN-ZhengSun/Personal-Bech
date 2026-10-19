from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApiCase(Base):
    """接口测试用例（Apifox 风格调试与用例库）。"""

    __tablename__ = "api_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET")
    url: Mapped[str] = mapped_column(Text, default="")
    # JSON 字符串：Headers 与 Query 用数组 [{key, value, enabled}]
    headers: Mapped[str] = mapped_column(Text, default="[]")
    query: Mapped[str] = mapped_column(Text, default="[]")
    # none / form / json / raw
    body_type: Mapped[str] = mapped_column(String(10), default="none")
    body: Mapped[str] = mapped_column(Text, default="")
    # JSON 字符串：断言数组 [{type, field, operator, value}]
    assertions: Mapped[str] = mapped_column(Text, default="[]")
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ApiEnv(Base):
    """接口测试环境（含基础 URL 与变量表）。"""

    __tablename__ = "api_env"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str] = mapped_column(String(300), default="")
    # JSON 字符串：变量表 {key: value}
    variables: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
