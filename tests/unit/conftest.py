"""Factories de fakes e helpers compartilhados pelos testes unitários."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from bson import ObjectId
from pwdlib import PasswordHash

from app.application.models import (
    ApiKeyDoc,
    ApplicationDoc,
    CustomerDoc,
    GeneratedApiKey,
    LogDoc,
    LogPage,
    UserDoc,
)

_pwd = PasswordHash.recommended()

# ── Constantes de teste ──────────────────────────────────────────────────────

CUSTOMER_ID = ObjectId()
APP_ID = ObjectId()
USER_ID = ObjectId()
LOG_ID = ObjectId()
JWT_SECRET = "test-secret-with-at-least-32-bytes!!"

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
FUTURE = NOW + timedelta(hours=2)
PAST = NOW - timedelta(hours=1)

RAW_KEY = "lx_testapikey1234567890abcdefghij12"
KEY_HASH = __import__("hashlib").sha256(RAW_KEY.encode()).hexdigest()
KEY_PREFIX = RAW_KEY[:10]

PASSWORD = "S3nh@F0rte!"
PASSWORD_HASH = _pwd.hash(PASSWORD)


# ── Factories ────────────────────────────────────────────────────────────────

def make_api_key(
    *,
    key_hash: str = KEY_HASH,
    prefix: str = KEY_PREFIX,
    expires_at: datetime | None = FUTURE,
    revoked_at: datetime | None = None,
) -> ApiKeyDoc:
    return ApiKeyDoc(
        key_hash=key_hash,
        prefix=prefix,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def make_application(
    *,
    id: ObjectId = APP_ID,
    customer_id: ObjectId = CUSTOMER_ID,
    name: str = "app-teste",
    api_keys: list[ApiKeyDoc] | None = None,
    tags: list[str] | None = None,
) -> ApplicationDoc:
    return ApplicationDoc(
        id=id,
        customer_id=customer_id,
        name=name,
        api_keys=api_keys if api_keys is not None else [make_api_key()],
        tags=tags or [],
        created_at=NOW,
    )


def make_customer(
    *,
    id: ObjectId = CUSTOMER_ID,
    name: str = "Acme",
    is_active: bool = True,
    retention_days: int = 30,
) -> CustomerDoc:
    return CustomerDoc(
        id=id,
        name=name,
        is_active=is_active,
        retention_days=retention_days,
        created_at=NOW,
    )


def make_user(
    *,
    id: ObjectId = USER_ID,
    customer_id: ObjectId = CUSTOMER_ID,
    name: str = "Fulano",
    email: str = "fulano@example.com",
    password_hash: str = PASSWORD_HASH,
) -> UserDoc:
    return UserDoc(
        id=id,
        customer_id=customer_id,
        name=name,
        email=email,
        password_hash=password_hash,
        created_at=NOW,
    )


def make_log(
    *,
    id: ObjectId = LOG_ID,
    customer_id: ObjectId = CUSTOMER_ID,
    application_id: ObjectId = APP_ID,
    level: int = 2,
    message: str = "ok",
    tags: list[str] | None = None,
) -> LogDoc:
    return LogDoc(
        id=id,
        customer_id=customer_id,
        application_id=application_id,
        application_name="app-teste",
        correlation_id=None,
        level=level,
        message=message,
        exception=None,
        environment="prod",
        information_data=None,
        tags=tags or [],
        occurred_at=NOW,
        received_at=NOW,
        expire_at=NOW + timedelta(days=30),
    )


# ── Mocks de repositório ─────────────────────────────────────────────────────

def mock_app_repo(**overrides) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_api_key_hash.return_value = overrides.get("by_hash", make_application())
    repo.find_by_id.return_value = overrides.get("by_id", make_application())
    repo.list_by_customer.return_value = overrides.get("list", [make_application()])
    repo.create.return_value = make_application()
    repo.add_api_key.return_value = None
    repo.revoke_api_key.return_value = overrides.get("revoked", True)
    return repo


def mock_customer_repo(**overrides) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id.return_value = overrides.get("by_id", make_customer())
    repo.create.return_value = make_customer()
    return repo


def mock_user_repo(**overrides) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_email.return_value = overrides.get("by_email", None)
    repo.find_by_id.return_value = overrides.get("by_id", make_user())
    repo.create.return_value = make_user()
    repo.list_by_customer.return_value = overrides.get("list", [make_user()])
    return repo


def mock_log_repo(**overrides) -> AsyncMock:
    repo = AsyncMock()
    repo.insert.return_value = LOG_ID
    repo.find_by_id.return_value = overrides.get("by_id", make_log())
    repo.list_by_customer.return_value = overrides.get(
        "page", LogPage(items=[make_log()], next_cursor=None)
    )
    return repo
