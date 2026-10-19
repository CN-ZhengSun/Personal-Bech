from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelConfig(Base):
    """AI 模型配置（多供应商）。"""

    __tablename__ = "model_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # doubao / openai / deepseek / other
    provider: Mapped[str] = mapped_column(String(20), default="doubao")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(300), default="")
    base_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    # enabled / disabled
    status: Mapped[str] = mapped_column(String(20), default="enabled")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Skill(Base):
    """AI 技能编排（用例生成、缺陷分析、报告生成等）。"""

    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    input_template: Mapped[str] = mapped_column(Text, default="")
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # draft / enabled / disabled
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PromptTemplate(Base):
    """Prompt 模板库。"""

    __tablename__ = "prompt_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    variables: Mapped[str | None] = mapped_column(String(300), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
