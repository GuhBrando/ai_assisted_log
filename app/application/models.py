"""Objetos de domínio compartilhados entre ports e use cases."""

from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId


@dataclass
class ApiKeyDoc:
    key_hash: str
    prefix: str
    expires_at: datetime | None
    revoked_at: datetime | None

    def is_valid(self, now: datetime) -> bool:
        if self.revoked_at is not None and self.revoked_at <= now:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return True


@dataclass
class ApplicationDoc:
    id: ObjectId
    customer_id: ObjectId
    name: str
    api_keys: list[ApiKeyDoc]
    tags: list[str]
    created_at: datetime


@dataclass
class CustomerDoc:
    id: ObjectId
    name: str
    is_active: bool
    retention_days: int
    created_at: datetime


@dataclass
class UserDoc:
    id: ObjectId
    customer_id: ObjectId
    name: str
    email: str
    password_hash: str
    created_at: datetime


@dataclass
class LogDoc:
    id: ObjectId
    customer_id: ObjectId
    application_id: ObjectId
    application_name: str
    correlation_id: object  # UUID | None
    level: int
    message: str
    exception: str | None
    environment: str
    information_data: dict | None
    tags: list[str]
    occurred_at: datetime
    received_at: datetime
    expire_at: datetime


@dataclass
class LogPage:
    items: list[LogDoc]
    next_cursor: str | None


@dataclass
class GeneratedApiKey:
    """Chave bruta exibida uma única vez + metadata."""
    raw_key: str
    prefix: str
    expires_at: datetime | None
