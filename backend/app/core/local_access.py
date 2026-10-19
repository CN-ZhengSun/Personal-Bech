"""本机部署边界：限制 Host 与浏览器来源，覆盖 HTTP 和 WebSocket。"""

from urllib.parse import urlsplit

from app.core.config import settings


class LocalAccessMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if not settings.LOCAL_ONLY or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
        host = headers.get("host", "").split(":", 1)[0].lower()
        origin = headers.get("origin", "")
        origin_host = (urlsplit(origin).hostname or "").lower() if origin else ""
        allowed = set(settings.ALLOWED_HOSTS)
        denied = host not in allowed or (origin_host and origin_host not in allowed)

        if denied and scope["type"] == "http":
            await send({"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": "禁止非本机访问".encode("utf-8")})
            return
        if denied and scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        await self.app(scope, receive, send)
