"""POST /applications — cadastra uma nova aplicação dentro do cliente."""

import re

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.application.errors import Conflict
from app.application.models import ApplicationDoc
from app.application.ports.application_repository import ApplicationRepository
from app.domain.constraints import MAX_TAGS, TAG_MAX_LENGTH, TAG_PATTERN

_TAG_RE = re.compile(TAG_PATTERN)


class RegisterApplication:
    def __init__(self, app_repo: ApplicationRepository) -> None:
        self._app_repo = app_repo

    async def execute(
        self,
        customer_id: ObjectId,
        name: str,
        tags: list[str],
    ) -> ApplicationDoc:
        normalized = _normalize_tags(tags)
        try:
            return await self._app_repo.create(customer_id, name, normalized)
        except DuplicateKeyError:
            raise Conflict("Já existe uma aplicação com esse nome neste cliente")


def _normalize_tags(tags: list[str]) -> list[str]:
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
    if len(normalized) > MAX_TAGS:
        from fastapi import HTTPException
        raise HTTPException(422, f"Máximo de {MAX_TAGS} tags por aplicação")
    return normalized
