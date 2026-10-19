from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MenuConfig(Base):
    """左侧菜单配置（分组 + 菜单项，统一排序）。"""

    __tablename__ = "menu_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # 菜单项：路由路径（如 /requirements）；分组行：None
    menu_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 显示名称（分组名 / 菜单名，均可修改）
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 菜单项所属分组标识；分组行：自身标识（如 test_manage）
    group_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
