from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.constraints import MAX_TAGS
from app.domain.log_level import LogLevel


class LogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: UUID | None = None
    level: LogLevel
    message: str = Field(min_length=1, max_length=32768)
    exception: str | None = Field(None, max_length=32768)
    environment: str = Field(min_length=1)
    information_data: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    occurred_at: datetime


class LogCreateResponse(BaseModel):
    id: str


class LogResponse(BaseModel):
    id: str
    customer_id: str
    application_id: str
    application_name: str
    correlation_id: UUID | None
    level: LogLevel
    message: str
    exception: str | None
    environment: str
    information_data: dict[str, Any] | None
    tags: list[str]
    occurred_at: datetime
    received_at: datetime
    expire_at: datetime


class LogListResponse(BaseModel):
    items: list[LogResponse]
    next_cursor: str | None
