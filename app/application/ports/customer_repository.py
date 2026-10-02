from abc import ABC, abstractmethod

from bson import ObjectId

from app.application.models import CustomerDoc


class CustomerRepository(ABC):
    @abstractmethod
    async def find_by_id(self, customer_id: ObjectId) -> CustomerDoc | None: ...

    @abstractmethod
    async def create(self, name: str, retention_days: int) -> CustomerDoc: ...

    @abstractmethod
    async def get_me(self, customer_id: ObjectId) -> CustomerDoc | None: ...
