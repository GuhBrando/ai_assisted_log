"""POST /auth/token — troca uma API key por um JWT de 1 hora (RN-16)."""

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.application.errors import Forbidden, NotAuthenticated
from app.application.ports.application_repository import ApplicationRepository
from app.application.ports.customer_repository import CustomerRepository


@dataclass
class TokenResult:
    access_token: str
    token_type: str
    expires_in: int


class IssueToken:
    def __init__(
        self,
        app_repo: ApplicationRepository,
        customer_repo: CustomerRepository,
    ) -> None:
        self._app_repo = app_repo
        self._customer_repo = customer_repo

    async def execute(self, raw_api_key: str) -> TokenResult:
        now = datetime.now(UTC)
        key_hash = _hash_key(raw_api_key)

        application = await self._app_repo.find_by_api_key_hash(key_hash)
        if application is None:
            raise NotAuthenticated

        api_key = next(
            (k for k in application.api_keys if k.key_hash == key_hash),
            None,
        )
        if api_key is None or not api_key.is_valid(now):
            raise NotAuthenticated

        customer = await self._customer_repo.find_by_id(application.customer_id)
        if customer is None or not customer.is_active:
            raise Forbidden

        # exp = min(now + 1h, api_key.expires_at) — RN-16
        exp = now + timedelta(hours=1)
        if api_key.expires_at is not None and api_key.expires_at < exp:
            exp = api_key.expires_at

        payload = {
            "sub": str(application.id),
            "iat": now,
            "exp": exp,
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")
        expires_in = int((exp - now).total_seconds())
        return TokenResult(access_token=token, token_type="bearer", expires_in=expires_in)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
