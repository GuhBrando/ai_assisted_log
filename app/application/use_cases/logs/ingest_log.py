"""POST /logs — valida e grava um log (RN-01 a RN-10, RN-15)."""

import json
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from bson import ObjectId

from app.application.errors import Forbidden, NotAuthenticated, PayloadTooLarge
from app.application.ports.application_repository import ApplicationRepository
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.log_repository import LogRepository
from app.domain.constraints import MAX_LOG_TAGS, MAX_TAGS, TAG_MAX_LENGTH, TAG_PATTERN

_INFO_DATA_LIMIT = 65_536  # 64 KB (RN-05)

_SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "senha",
        "cpf",
        "card",
        "credit_card",
        "creditcard",
        "cvv",
        "ssn",
        "token",
        "secret",
        "api_key",
        "apikey",
        "pin",
    }
)

_TAG_RE = re.compile(TAG_PATTERN)


class IngestLog:
    def __init__(
        self,
        app_repo: ApplicationRepository,
        customer_repo: CustomerRepository,
        log_repo: LogRepository,
    ) -> None:
        self._app_repo = app_repo
        self._customer_repo = customer_repo
        self._log_repo = log_repo

    async def execute(
        self,
        app_id_str: str,
        correlation_id: UUID | None,
        level: int,
        message: str,
        exception: str | None,
        environment: str,
        information_data: dict | None,
        tags: list[str],
        occurred_at: datetime,
    ) -> ObjectId:
        app_id = ObjectId(app_id_str)

        application = await self._app_repo.find_by_id(app_id)
        if application is None:
            raise NotAuthenticated

        customer = await self._customer_repo.find_by_id(application.customer_id)
        if customer is None or not customer.is_active:
            raise Forbidden

        # Valida e normaliza tags do log (422 tratado pelo router se ValidationError)
        log_tags = _normalize_tags(tags, MAX_TAGS)

        # Mescla: tags da aplicação têm precedência (RN-15)
        app_tag_keys = {t.split(":")[0] for t in application.tags}
        merged_tags = list(application.tags) + [t for t in log_tags if t.split(":")[0] not in app_tag_keys]
        if len(merged_tags) > MAX_LOG_TAGS:
            merged_tags = merged_tags[:MAX_LOG_TAGS]

        # Valida information_data (RN-05)
        if information_data is not None:
            _validate_info_data(information_data)
            information_data = _mask_sensitive(information_data)

        received_at = datetime.now(UTC)
        expire_at = received_at + timedelta(days=customer.retention_days)

        log_id = await self._log_repo.insert(
            customer_id=customer.id,
            application_id=application.id,
            application_name=application.name,
            correlation_id=correlation_id,
            level=level,
            message=message,
            exception=exception,
            environment=environment,
            information_data=information_data,
            tags=merged_tags,
            occurred_at=occurred_at,
            received_at=received_at,
            expire_at=expire_at,
        )
        return log_id


def _normalize_tags(tags: list[str], max_count: int) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        t = raw.strip().lower()
        if not _TAG_RE.match(t):
            from fastapi import HTTPException
            raise HTTPException(422, f"Tag inválida: {raw!r}")
        if len(t) > TAG_MAX_LENGTH:
            from fastapi import HTTPException
            raise HTTPException(422, f"Tag muito longa: {raw!r}")
        if t not in seen:
            seen.add(t)
            normalized.append(t)
    if len(normalized) > max_count:
        from fastapi import HTTPException
        raise HTTPException(422, f"Máximo de {max_count} tags por log")
    return normalized


def _validate_info_data(data: dict, _path: str = "") -> None:
    """Verifica chaves com $ ou . e tamanho ≤ 64 KB (RN-05)."""
    try:
        size = len(json.dumps(data, default=str).encode())
    except Exception:
        size = 0
    if size > _INFO_DATA_LIMIT:
        raise PayloadTooLarge

    _check_keys(data)


def _check_keys(data: object) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if "$" in key or "." in key:
                from fastapi import HTTPException
                raise HTTPException(422, f"Chave proibida em information_data: {key!r}")
            _check_keys(value)
    elif isinstance(data, list):
        for item in data:
            _check_keys(item)


def _mask_sensitive(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_FIELDS:
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = _mask_sensitive(value)
        else:
            result[key] = value
    return result
