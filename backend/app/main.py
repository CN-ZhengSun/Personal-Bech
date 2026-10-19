from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

import app.models  # noqa: F401  # 注册全部 ORM 模型到 Base.metadata
from app.api.v1 import (
    adbtools,
    ai_router,
    apitest,
    auth,
    automation,
    bugs,
    cases,
    dashboard,
    executions,
    jmeter,
    knowledge,
    menu,
    plans,
    projects,
    releases,
    requirements,
    tracking,
    upload,
)
from app.api.v1.tracking import ws_router as tracking_ws_router
from app.api.v1.adbtools import ws_router as adb_ws_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.operation_log import OperationLogMiddleware
from app.core.local_access import LocalAccessMiddleware
from app.core.security import get_current_user
from app.api.v1.upload import UPLOAD_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（正式环境建议改用 Alembic 迁移）
    Base.metadata.create_all(bind=engine)
    _migrate_knowledge_columns()
    yield


def _migrate_knowledge_columns():
    """轻量幂等迁移：为已存在的 knowledge_doc 表补充附件/检索字段（MySQL）。"""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        if "knowledge_doc" not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns("knowledge_doc")}
        adds = {
            "file_url": "VARCHAR(500) NULL",
            "file_name": "VARCHAR(255) NULL",
            "file_size": "INT NULL",
            "file_type": "VARCHAR(20) NULL",
            "search_text": "TEXT NULL",
        }
        with engine.begin() as conn:
            for col, ddl in adds.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE knowledge_doc ADD COLUMN {col} {ddl}"))
    except Exception as exc:  # pragma: no cover - 迁移失败不应阻断服务启动
        print(f"[migrate] knowledge_doc columns skipped: {exc}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="一站式测试管理平台 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(OperationLogMiddleware)
app.add_middleware(LocalAccessMiddleware)


@app.get("/health", tags=["system"])
def health():
    """健康检查：返回服务状态与数据库连通性。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # pragma: no cover
        db_status = f"error: {exc}"
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
    }


# 认证（无需鉴权）
app.include_router(auth.router, prefix="/api/v1")
# PRD 独立挂载（/api/v1/prd）
app.include_router(requirements.prd_router, prefix="/api/v1")
# 业务模块（统一 /api/v1 前缀）
for r in (
    projects.router,
    requirements.router,
    plans.router,
    cases.router,
    executions.router,
    jmeter.router,
    bugs.router,
    automation.router,
    releases.router,
    knowledge.router,
    menu.router,
    ai_router.router,
    dashboard.router,
    upload.router,
    tracking.router,
    adbtools.router,
    apitest.router,
):
    app.include_router(r, prefix="/api/v1")

# 埋点监控 WebSocket（独立挂载，无 /api/v1 前缀，使用会话鉴权）
app.include_router(tracking_ws_router)
# ADB 工具 WebSocket
app.include_router(adb_ws_router)

# 附件读取也必须经过会话校验，并阻止目录穿越。
@app.get("/uploads/{file_path:path}", include_in_schema=False)
def uploaded_file(file_path: str, _=Depends(get_current_user)):
    root = UPLOAD_DIR.resolve()
    target = (root / file_path).resolve()
    if root != target and root not in target.parents:
        raise HTTPException(status_code=404, detail="附件不存在")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="附件不存在")
    return FileResponse(target)
