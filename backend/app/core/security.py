import base64
import hashlib
import hmac
import secrets
import time
from pathlib import Path

from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User


def _load_secret() -> str:
    """环境变量优先；本机模式首次启动时生成并持久化随机密钥。"""
    if settings.APP_SECRET_KEY:
        return settings.APP_SECRET_KEY
    path = Path(__file__).resolve().parents[2] / ".app_secret"
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding="utf-8")
    return value


SECRET = _load_secret()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, n, r, p, salt, expected = password_hash.split("$", 5)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def _password_marker(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def create_token(user_id: int, password_hash: str) -> str:
    now = int(time.time())
    expires = now + settings.SESSION_DAYS * 24 * 60 * 60
    marker = _password_marker(password_hash)
    payload = base64.urlsafe_b64encode(f"{user_id}:{now}:{expires}:{marker}".encode("utf-8")).decode("utf-8")
    sig = hmac.new(SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_token(token: str) -> int | None:
    try:
        payload, sig = token.split(".")
        expected = hmac.new(SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        raw = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        parts = raw.split(":")
        now = int(time.time())
        if len(parts) != 4:
            return None
        user_id, _, expires, _ = parts
        if int(expires) < now:
            return None
        return int(user_id)
    except Exception:
        return None


def token_matches_password(token: str, password_hash: str) -> bool:
    """密码修改后让此前签发的会话立即失效。"""
    try:
        payload = token.split(".", 1)[0]
        parts = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8").split(":")
        return len(parts) == 4 and hmac.compare_digest(parts[3], _password_marker(password_hash))
    except Exception:
        return False


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """解析 HttpOnly 会话。"""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效")
    user = db.get(User, user_id)
    if (
        not user
        or user.status != "active"
        or user.role != "admin"
        or not token_matches_password(token, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def get_current_websocket_user(websocket: WebSocket, db: Session = Depends(get_db)) -> User:
    token = websocket.cookies.get(settings.SESSION_COOKIE_NAME, "")
    user_id = verify_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    if (
        not user
        or user.status != "active"
        or user.role != "admin"
        or not token_matches_password(token, user.password_hash)
    ):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return user
