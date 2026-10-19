from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrackingEvent(Base):
    """埋点清单与触发计数（按项目隔离）。"""

    __tablename__ = "tracking_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(200), index=True)  # 事件ID（eid），匹配基准
    event_name: Mapped[str] = mapped_column(String(200), default="")  # 事件名称
    operation: Mapped[str] = mapped_column(Text, default="")  # 触发操作/打点含义
    meaning: Mapped[str] = mapped_column(Text, default="")
    is_ignored: Mapped[int] = mapped_column(Integer, default=0)  # 0=正常 1=忽略（清单忽略，不参与监控匹配）
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)  # 触发次数
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TrackingConfig(Base):
    """埋点采集配置（每项目一条）。"""

    __tablename__ = "tracking_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"), unique=True, index=True)
    # adb / mitmproxy
    collect_type: Mapped[str] = mapped_column(String(20), default="adb")
    log_tag: Mapped[str] = mapped_column(String(100), default="EM")  # 日志TAG过滤
    batch_rule: Mapped[str] = mapped_column(Text, default="")  # 批量拆分规则（预留）
    domains: Mapped[str] = mapped_column(Text, default="[]")  # 埋点上报域名 JSON
    dedup_window: Mapped[int] = mapped_column(Integer, default=3)  # 去重时间窗口（秒）
    # running / stopped
    status: Mapped[str] = mapped_column(String(20), default="stopped")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
