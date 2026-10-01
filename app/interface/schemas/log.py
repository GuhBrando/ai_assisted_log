from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.constraints import MAX_TAGS
from app.domain.log_level import LogLevel
from app.domain.tags import Tag


class LogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: UUID | None = None
    level: LogLevel
    message: str = Field(min_length=1, max_length=32768)
    exception: str | None = Field(None, max_length=32768)
    environment: str = Field(min_length=1)
    information_data: dict[str, Any] | None = None
    tags: list[Tag] = Field(default_factory=list)
    occurred_at: datetime

    @field_validator("tags", mode="after")
    @classmethod
    def deduplicate_and_limit(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result = [t for t in v if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]
        if len(result) > MAX_TAGS:
            raise ValueError(f"Máximo de {MAX_TAGS} tags por log")
        return result


class LogRead(BaseModel):
    """Resposta de GET /logs e GET /logs/{id} (vocabulário do domínio: LogRead)."""
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


class LogCreateResponse(BaseModel):
    """Resposta de POST /logs — só o id gerado."""
    id: str


class LogListResponse(BaseModel):
    items: list[LogRead]
    next_cursor: str | None
