from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class UserLogin(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    username: str
    display_name: str
    email: str | None
    role: str
    status: str
    created_at: datetime


class Token(BaseModel):
    user: UserOut
