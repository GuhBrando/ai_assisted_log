from datetime import UTC, datetime

from bson import ObjectId

from app.application.models import CustomerDoc
from app.application.ports.customer_repository import CustomerRepository
from app.infrastructure.mongodb.client import MongoDatabase


class MongoCustomerRepository(CustomerRepository):
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db["customers"]

    async def find_by_id(self, customer_id: ObjectId) -> CustomerDoc | None:
        doc = await self._col.find_one({"_id": customer_id})
        return _to_domain(doc) if doc else None

    async def get_me(self, customer_id: ObjectId) -> CustomerDoc | None:
        return await self.find_by_id(customer_id)

    async def create(self, name: str, retention_days: int) -> CustomerDoc:
        now = datetime.now(UTC)
        doc = {
            "name": name,
            "isActive": True,
            "retentionDays": retention_days,
            "createdAt": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _to_domain(doc)


def _to_domain(doc: dict) -> CustomerDoc:
    return CustomerDoc(
        id=doc["_id"],
        name=doc["name"],
        is_active=doc["isActive"],
        retention_days=doc["retentionDays"],
        created_at=doc["createdAt"],
    )
