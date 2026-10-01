"""GET /logs — lista logs com filtros e paginação por cursor (RN-09, RN-14)."""

from datetime import datetime
from uuid import UUID

from bson import ObjectId

from app.application.models import LogPage
from app.application.ports.log_repository import LogRepository


class QueryLogs:
    def __init__(self, log_repo: LogRepository) -> None:
        self._log_repo = log_repo

    async def execute(
        self,
        customer_id: ObjectId,
        application_id: ObjectId | None = None,
        level_min: int | None = None,
        correlation_id: UUID | None = None,
        tags: list[str] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> LogPage:
        limit = min(max(limit, 1), 100)
        return await self._log_repo.list_by_customer(
            customer_id=customer_id,
            application_id=application_id,
            level_min=level_min,
            correlation_id=correlation_id,
            tags=tags or [],
            from_date=from_date,
            to_date=to_date,
            cursor=cursor,
            limit=limit,
        )
