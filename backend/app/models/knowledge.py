from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeDoc(Base):
    """知识库文档：支持附件文件（uploads 内路径）或纯文本内容。"""

    __tablename__ = "knowledge_doc"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(50), default="通用")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # project / global
    visibility: Mapped[str] = mapped_column(String(20), default="global")
    # 附件文件信息（文件保存在项目内 uploads/knowledge/ 下，便于整体迁移）
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 全文检索用文本：标题+标签+分类+文件提取内容（图片等无法提取则为空）
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
