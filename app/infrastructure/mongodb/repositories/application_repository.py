from datetime import UTC, datetime

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.application.errors import Conflict
from app.application.models import ApiKeyDoc, ApplicationDoc
from app.application.ports.application_repository import ApplicationRepository
from app.infrastructure.mongodb.client import MongoDatabase


class MongoApplicationRepository(ApplicationRepository):
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db["applications"]

    async def find_by_api_key_hash(self, key_hash: str) -> ApplicationDoc | None:
        doc = await self._col.find_one({"apiKeys.keyHash": key_hash})
        return _to_domain(doc) if doc else None

    async def find_by_id(self, app_id: ObjectId) -> ApplicationDoc | None:
        doc = await self._col.find_one({"_id": app_id})
        return _to_domain(doc) if doc else None

    async def list_by_customer(self, customer_id: ObjectId) -> list[ApplicationDoc]:
        cursor = self._col.find({"customerId": customer_id})
        return [_to_domain(doc) async for doc in cursor]

    async def create(
        self,
        customer_id: ObjectId,
        name: str,
        tags: list[str],
    ) -> ApplicationDoc:
        now = datetime.now(UTC)
        doc = {
            "customerId": customer_id,
            "name": name,
            "apiKeys": [],
            "tags": tags,
            "createdAt": now,
        }
        try:
            result = await self._col.insert_one(doc)
        except DuplicateKeyError as e:
            index = e.details.get("keyPattern", {}) if e.details else {}
            if "name" in str(index):
                raise Conflict("Já existe uma aplicação com esse nome neste cliente (applications_customer_name_unique)")
            raise Conflict("Conflito de unicidade")
        doc["_id"] = result.inserted_id
        return _to_domain(doc)

    async def add_api_key(
        self,
        app_id: ObjectId,
        key_hash: str,
        prefix: str,
        expires_at: datetime | None,
    ) -> None:
        api_key = {
            "keyHash": key_hash,
            "prefix": prefix,
            "expiresAt": expires_at,
            "revokedAt": None,
        }
        await self._col.update_one(
            {"_id": app_id, "apiKeys.prefix": {"$ne": prefix}},
            {"$push": {"apiKeys": api_key}},
        )

    async def revoke_api_key(self, app_id: ObjectId, prefix: str) -> bool:
        now = datetime.now(UTC)
        result = await self._col.update_one(
            {"_id": app_id, "apiKeys.prefix": prefix, "apiKeys.revokedAt": None},
            {"$set": {"apiKeys.$.revokedAt": now}},
        )
        return result.modified_count > 0


def _to_domain(doc: dict) -> ApplicationDoc:
    return ApplicationDoc(
        id=doc["_id"],
        customer_id=doc["customerId"],
        name=doc["name"],
        api_keys=[
            ApiKeyDoc(
                key_hash=k["keyHash"],
                prefix=k["prefix"],
                expires_at=k.get("expiresAt"),
                revoked_at=k.get("revokedAt"),
            )
            for k in doc.get("apiKeys", [])
        ],
        tags=doc.get("tags", []),
        created_at=doc["createdAt"],
    )
