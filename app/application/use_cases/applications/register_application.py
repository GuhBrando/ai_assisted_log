"""POST /applications — cadastra uma nova aplicação dentro do cliente."""

from bson import ObjectId

from app.application.models import ApplicationDoc
from app.application.ports.application_repository import ApplicationRepository


class RegisterApplication:
    def __init__(self, app_repo: ApplicationRepository) -> None:
        self._app_repo = app_repo

    async def execute(
        self,
        customer_id: ObjectId,
        name: str,
        tags: list[str],
    ) -> ApplicationDoc:
        # Tags already normalized/deduplicated by Pydantic schema (list[Tag])
        return await self._app_repo.create(customer_id, name, tags)
