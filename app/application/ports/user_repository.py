from abc import ABC, abstractmethod

from bson import ObjectId

from app.application.models import UserDoc


class UserRepository(ABC):
    @abstractmethod
    async def find_by_email(self, email: str) -> UserDoc | None: ...

    @abstractmethod
    async def find_by_id(self, user_id: ObjectId) -> UserDoc | None: ...

    @abstractmethod
    async def list_by_customer(self, customer_id: ObjectId) -> list[UserDoc]: ...

    @abstractmethod
    async def create(
        self,
        customer_id: ObjectId,
        name: str,
        email: str,
        password_hash: str,
    ) -> UserDoc: ...
