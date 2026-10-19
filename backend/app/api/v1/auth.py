import hmac

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import PasswordChange, Token, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: User):
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=create_token(user.id, user.password_hash),
        max_age=settings.SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=not settings.LOCAL_ONLY,
        samesite="strict",
        path="/",
    )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="本机工作台仅允许管理员账号登录")
    _set_session_cookie(response, user)
    return Token(user=user)


@router.get("/me", response_model=UserOut)
def me(response: Response, current: User = Depends(get_current_user)):
    # 每次打开工作台续期，日常使用无需重复登录。
    _set_session_cookie(response, current)
    return current


@router.post("/change-password", status_code=204)
def change_password(
    payload: PasswordChange,
    response: Response,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    if hmac.compare_digest(payload.current_password, payload.new_password):
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    current.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(current)
    _set_session_cookie(response, current)
    current.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(current)
    _set_session_cookie(response, current)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/", samesite="strict")
