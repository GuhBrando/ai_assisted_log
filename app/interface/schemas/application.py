from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.constraints import MAX_TAGS
from app.domain.tags import Tag


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    tags: list[Tag] = Field(default_factory=list)

    @field_validator("tags", mode="after")
    @classmethod
    def deduplicate_and_limit(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result = [t for t in v if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]
        if len(result) > MAX_TAGS:
            raise ValueError(f"Máximo de {MAX_TAGS} tags por aplicação")
        return result


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
