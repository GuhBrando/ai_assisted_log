from datetime import UTC, datetime

from bson import ObjectId

from app.application.models import UserDoc
from app.application.ports.user_repository import UserRepository
from app.infrastructure.mongodb.client import MongoDatabase


class MongoUserRepository(UserRepository):
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db["users"]

    async def find_by_email(self, email: str) -> UserDoc | None:
        doc = await self._col.find_one({"email": email})
        return _to_domain(doc) if doc else None

    async def find_by_id(self, user_id: ObjectId) -> UserDoc | None:
        doc = await self._col.find_one({"_id": user_id})
        return _to_domain(doc) if doc else None

    async def list_by_customer(self, customer_id: ObjectId) -> list[UserDoc]:
        cursor = self._col.find({"customerId": customer_id})
        return [_to_domain(doc) async for doc in cursor]

    async def create(
        self,
        customer_id: ObjectId,
        name: str,
        email: str,
        password_hash: str,
    ) -> UserDoc:
        now = datetime.now(UTC)
        doc = {
            "customerId": customer_id,
            "name": name,
            "email": email,
            "passwordHash": password_hash,
            "createdAt": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _to_domain(doc)


def _to_domain(doc: dict) -> UserDoc:
    return UserDoc(
        id=doc["_id"],
        customer_id=doc["customerId"],
        name=doc["name"],
        email=doc["email"],
        password_hash=doc["passwordHash"],
        created_at=doc["createdAt"],
    )
