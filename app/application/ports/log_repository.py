from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from bson import ObjectId

from app.application.models import LogDoc, LogPage


class LogRepository(ABC):
    @abstractmethod
    async def insert(
        self,
        customer_id: ObjectId,
        application_id: ObjectId,
        application_name: str,
        correlation_id: UUID | None,
        level: int,
        message: str,
        exception: str | None,
        environment: str,
        information_data: dict | None,
        tags: list[str],
        occurred_at: datetime,
        received_at: datetime,
        expire_at: datetime,
    ) -> ObjectId: ...

    @abstractmethod
    async def find_by_id(self, log_id: ObjectId, customer_id: ObjectId) -> LogDoc | None: ...

    @abstractmethod
    async def list_by_customer(
        self,
        customer_id: ObjectId,
        application_id: ObjectId | None,
        level_min: int | None,
        correlation_id: UUID | None,
        tags: list[str],
        from_date: datetime | None,
        to_date: datetime | None,
        cursor: str | None,
        limit: int,
    ) -> LogPage: ...
