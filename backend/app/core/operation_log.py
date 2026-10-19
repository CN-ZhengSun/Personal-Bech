"""操作审计日志中间件：自动记录所有 /api/v1 写操作（POST/PATCH/PUT/DELETE）。"""
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware


def parse_target(path: str):
    """从 /api/v1/bugs/5/comments 提取 target_type=bug, target_id=5。"""
    segs = [s for s in path.split("/") if s]
    if "api" in segs:
        idx = segs.index("api")
        segs = segs[idx + 2:]  # 跳过 api, v1
    if not segs:
        return None, None
    ttype = segs[0]
    tid = None
    for s in segs[1:]:
        if s.isdigit():
            tid = int(s)
            break
    return ttype, tid


class OperationLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        method = request.method
        if (
            path.startswith("/api/v1")
            and not path.startswith("/api/v1/auth")
            and method in ("POST", "PATCH", "PUT", "DELETE")
            and response.status_code < 400
        ):
            try:
                await run_in_threadpool(self._write_log, request, method, path)
            except Exception:  # 日志失败不影响主流程
                pass
        return response

    def _write_log(self, request, method, path):
        from app.core.database import SessionLocal
        from app.core.config import settings
        from app.core.security import verify_token
        from app.models.operation_log import OperationLog
        from app.models.user import User

        username = None
        token = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
        if token:
            uid = verify_token(token)
            if uid is not None:
                db = SessionLocal()
                try:
                    u = db.get(User, uid)
                    username = (u.display_name or u.username) if u else None
                finally:
                    db.close()

        ttype, tid = parse_target(path)
        action = {"POST": "创建", "PATCH": "更新", "PUT": "更新", "DELETE": "删除"}.get(method, method)

        db = SessionLocal()
        try:
            db.add(
                OperationLog(
                    user=username,
                    action=action,
                    target_type=ttype,
                    target_id=tid,
                    detail=f"{method} {path}",
                )
            )
            db.commit()
        finally:
            db.close()
