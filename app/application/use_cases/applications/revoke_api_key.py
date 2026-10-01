"""POST /applications/{id}/api-keys/{prefix}/revoke — revoga uma API key."""

from bson import ObjectId

from app.application.errors import NotFound
from app.application.ports.application_repository import ApplicationRepository


class RevokeApiKey:
    def __init__(self, app_repo: ApplicationRepository) -> None:
        self._app_repo = app_repo

    async def execute(
        self,
        customer_id: ObjectId,
        app_id: ObjectId,
        prefix: str,
    ) -> None:
        application = await self._app_repo.find_by_id(app_id)
        if application is None or application.customer_id != customer_id:
            raise NotFound

        revoked = await self._app_repo.revoke_api_key(app_id, prefix)
        if not revoked:
            raise NotFound
