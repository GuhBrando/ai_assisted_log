from abc import ABC, abstractmethod
from datetime import datetime

from bson import ObjectId

from app.application.models import ApplicationDoc


class ApplicationRepository(ABC):
    @abstractmethod
    async def find_by_api_key_hash(self, key_hash: str) -> ApplicationDoc | None: ...

    @abstractmethod
    async def find_by_id(self, app_id: ObjectId) -> ApplicationDoc | None: ...

    @abstractmethod
    async def list_by_customer(self, customer_id: ObjectId) -> list[ApplicationDoc]: ...

    @abstractmethod
    async def create(
        self,
        customer_id: ObjectId,
        name: str,
        tags: list[str],
    ) -> ApplicationDoc: ...

    @abstractmethod
    async def add_api_key(
        self,
        app_id: ObjectId,
        key_hash: str,
        prefix: str,
        expires_at: datetime | None,
    ) -> None: ...

    @abstractmethod
    async def revoke_api_key(self, app_id: ObjectId, prefix: str) -> bool: ...
