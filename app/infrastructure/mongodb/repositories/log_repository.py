import base64
import json
from datetime import UTC, datetime
from uuid import UUID

from bson import ObjectId

from app.application.models import LogDoc, LogPage
from app.application.ports.log_repository import LogRepository
from app.infrastructure.mongodb.client import MongoDatabase


class MongoLogRepository(LogRepository):
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db["logs"]

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
    ) -> ObjectId:
        doc = {
            "customerId": customer_id,
            "applicationId": application_id,
            "applicationName": application_name,
            "correlationId": correlation_id,
            "level": level,
            "message": message,
            "exception": exception,
            "environment": environment,
            "informationData": information_data,
            "tags": tags,
            "occurredAt": occurred_at,
            "receivedAt": received_at,
            "expireAt": expire_at,
        }
        result = await self._col.insert_one(doc)
        return result.inserted_id

    async def find_by_id(self, log_id: ObjectId, customer_id: ObjectId) -> LogDoc | None:
        doc = await self._col.find_one({"_id": log_id, "customerId": customer_id})
        return _to_domain(doc) if doc else None

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
    ) -> LogPage:
        query: dict = {"customerId": customer_id}

        if application_id is not None:
            query["applicationId"] = application_id
        if level_min is not None:
            # Usar $in com os valores da faixa (ADR na DDL de logs)
            query["level"] = {"$in": list(range(level_min, 6))}
        if correlation_id is not None:
            query["correlationId"] = correlation_id
        if tags:
            query["tags"] = {"$all": tags}

        occurred_filter: dict = {}
        if from_date is not None:
            occurred_filter["$gte"] = from_date
        if to_date is not None:
            occurred_filter["$lte"] = to_date
        if occurred_filter:
            query["occurredAt"] = occurred_filter

        if cursor is not None:
            cursor_data = _decode_cursor(cursor)
            if cursor_data:
                cursor_occurred_at, cursor_id = cursor_data
                query["$or"] = [
                    {"occurredAt": {"$lt": cursor_occurred_at}},
                    {"occurredAt": cursor_occurred_at, "_id": {"$lt": cursor_id}},
                ]

        docs = await self._col.find(query).sort(
            [("occurredAt", -1), ("_id", -1)]
        ).limit(limit + 1).to_list()

        has_next = len(docs) > limit
        items = docs[:limit]

        next_cursor = None
        if has_next and items:
            last = items[-1]
            next_cursor = _encode_cursor(last["occurredAt"], last["_id"])

        return LogPage(items=[_to_domain(d) for d in items], next_cursor=next_cursor)


def _encode_cursor(occurred_at: datetime, doc_id: ObjectId) -> str:
    data = {"occurred_at": occurred_at.isoformat(), "id": str(doc_id)}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, ObjectId] | None:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        occurred_at = datetime.fromisoformat(data["occurred_at"])
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        return occurred_at, ObjectId(data["id"])
    except Exception:
        return None


def _to_domain(doc: dict) -> LogDoc:
    return LogDoc(
        id=doc["_id"],
        customer_id=doc["customerId"],
        application_id=doc["applicationId"],
        application_name=doc["applicationName"],
        correlation_id=doc.get("correlationId"),
        level=doc["level"],
        message=doc["message"],
        exception=doc.get("exception"),
        environment=doc["environment"],
        information_data=doc.get("informationData"),
        tags=doc.get("tags", []),
        occurred_at=doc["occurredAt"],
        received_at=doc["receivedAt"],
        expire_at=doc["expireAt"],
    )
