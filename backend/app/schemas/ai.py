from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.schemas.common import ORMModel


class ModelConfigCreate(BaseModel):
    name: str
    provider: str = "doubao"
    model_name: str
    api_key: str = ""
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    status: str = "enabled"


class ModelConfigUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    status: str | None = None


class ModelConfigOut(ORMModel):
    id: int
    name: str
    provider: str
    model_name: str
    api_key: str
    base_url: str | None
    temperature: float
    max_tokens: int
    status: str
    created_at: datetime

    @field_serializer("api_key")
    def mask_api_key(self, value: str) -> str:
        if not value:
            return ""
        return f"{value[:3]}****{value[-4:]}" if len(value) > 7 else "******"


class SkillCreate(BaseModel):
    name: str
    description: str = ""
    input_template: str = ""
    prompt_template: str = ""
    model_id: int | None = None
    status: str = "draft"


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    input_template: str | None = None
    prompt_template: str | None = None
    model_id: int | None = None
    status: str | None = None


class SkillOut(ORMModel):
    id: int
    name: str
    description: str
    input_template: str
    prompt_template: str
    model_id: int | None
    status: str
    version: str
    created_at: datetime
    updated_at: datetime


class PromptTemplateCreate(BaseModel):
    name: str
    content: str = ""
    variables: str | None = None


class PromptTemplateOut(ORMModel):
    id: int
    name: str
    content: str
    variables: str | None
    version: str
    status: str
    created_at: datetime
