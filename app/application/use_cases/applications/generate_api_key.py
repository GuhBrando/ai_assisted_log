"""POST /applications/{id}/api-keys — gera uma nova API key para uma aplicação."""

import hashlib
import secrets
from datetime import datetime

from bson import ObjectId

from app.application.errors import NotFound
from app.application.models import GeneratedApiKey
from app.application.ports.application_repository import ApplicationRepository


class GenerateApiKey:
    def __init__(self, app_repo: ApplicationRepository) -> None:
        self._app_repo = app_repo

    async def execute(
        self,
        customer_id: ObjectId,
        app_id: ObjectId,
        expires_at: datetime | None,
    ) -> GeneratedApiKey:
        application = await self._app_repo.find_by_id(app_id)
        if application is None or application.customer_id != customer_id:
            raise NotFound

        raw_key = "lx_" + secrets.token_urlsafe(32)
        prefix = raw_key[:10]  # "lx_" + 7 chars
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        await self._app_repo.add_api_key(app_id, key_hash, prefix, expires_at)
        return GeneratedApiKey(raw_key=raw_key, prefix=prefix, expires_at=expires_at)
