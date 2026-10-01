from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.constraints import MAX_TAGS


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)


class ApplicationResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    tags: list[str]
    created_at: datetime


class ApiKeyResponse(BaseModel):
    prefix: str
    raw_key: str
    expires_at: datetime | None


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_at: datetime | None = None
