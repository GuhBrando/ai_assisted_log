"""DDL de `log_metrics_hourly`: fato agregado do modelo dimensional (ADR-021, proposta).

Grão: um documento por cliente × aplicação × ambiente × nível × hora (UTC) de `occurredAt`, com a
quantidade de logs. Serve os gráficos do painel sem varrer a coleção `logs`.

É uma visão materializada: só `refresh_log_metrics` grava aqui, recalculando horas inteiras a
partir de `logs`. O documento expira junto com o último log da hora (`expireAt` = maior
`expireAt` dos logs), então a retenção de cada cliente vale também para os agregados.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.infrastructure.mongodb.client import MongoDatabase
from app.infrastructure.mongodb.ddl import logs
from app.infrastructure.mongodb.ddl.fields import LEVEL
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

NAME = "log_metrics_hourly"

GRAIN = ("customerId", "applicationId", "environment", "level", "bucketStart")

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", *GRAIN, "count", "expireAt"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "customerId": {"bsonType": "objectId"},
            "applicationId": {"bsonType": "objectId"},
            "environment": {"bsonType": "string", "minLength": 1},
            "level": LEVEL,
            "bucketStart": {"bsonType": "date", "description": "Início da hora, em UTC."},
            "count": {"bsonType": ["int", "long"], "minimum": 1},
            "expireAt": {"bsonType": "date"},
        },
    }
}

INDEXES = (
    # Único no grão: é a chave do $merge. Cliente e hora na frente servem o painel (cliente + período).
    IndexModel(
        [
            ("customerId", ASCENDING),
            ("bucketStart", DESCENDING),
            ("applicationId", ASCENDING),
            ("environment", ASCENDING),
            ("level", ASCENDING),
        ],
        name="log_metrics_hourly_grain_unique",
        unique=True,
    ),
    IndexModel([("expireAt", ASCENDING)], name="log_metrics_hourly_expire_ttl", expireAfterSeconds=0),
)

SPEC = CollectionSpec(NAME, VALIDATOR, INDEXES)

_HOUR = timedelta(hours=1)
_HOUR_OF_OCCURRED_AT = {"$dateTrunc": {"date": "$occurredAt", "unit": "hour"}}


async def refresh_log_metrics(db: MongoDatabase, received_since: datetime) -> int:
    """Recalcula as horas que receberam logs desde `received_since` e devolve quantas foram.

    Idempotente: cada hora é recalculada inteira e substitui a anterior, então janelas sobrepostas
    não contam duas vezes. Logs atrasados (`occurredAt` antigo) entram, porque a busca é pela
    chegada (`_id`), não por `occurredAt`.

    É um job da plataforma: lê logs de todos os clientes pelo índice de `_id`, sem criar índice
    novo em `logs`, e grava agregados sempre separados por `customerId`.
    """
    touched = await db[logs.NAME].aggregate(
        [
            {"$match": {"_id": {"$gte": ObjectId.from_datetime(received_since)}}},
            {"$group": {"_id": {"customerId": "$customerId", "bucketStart": _HOUR_OF_OCCURRED_AT}}},
        ]
    )
    hours_by_customer: defaultdict[ObjectId, list[datetime]] = defaultdict(list)
    async for doc in touched:
        hours_by_customer[doc["_id"]["customerId"]].append(doc["_id"]["bucketStart"])

    # Um cliente por vez: é um job de fundo e não deve disputar o banco com a ingestão.
    for customer_id, hours in hours_by_customer.items():
        await _recompute_hours(db, customer_id, hours)
    return sum(len(hours) for hours in hours_by_customer.values())


async def _recompute_hours(db: MongoDatabase, customer_id: ObjectId, hours: list[datetime]) -> None:
    pipeline = [
        {
            "$match": {
                "customerId": customer_id,
                "$or": [{"occurredAt": {"$gte": hour, "$lt": hour + _HOUR}} for hour in hours],
            }
        },
        {
            "$group": {
                "_id": {
                    "applicationId": "$applicationId",
                    "environment": "$environment",
                    "level": "$level",
                    "bucketStart": _HOUR_OF_OCCURRED_AT,
                },
                "count": {"$sum": 1},
                "expireAt": {"$max": "$expireAt"},
            }
        },
        {
            "$replaceWith": {
                "$mergeObjects": [
                    "$_id",
                    {"customerId": customer_id, "count": "$count", "expireAt": "$expireAt"},
                ]
            }
        },
        {"$merge": {"into": NAME, "on": list(GRAIN), "whenMatched": "replace", "whenNotMatched": "insert"}},
    ]
    # Com $merge, o próprio comando aggregate grava; o cursor devolvido vem vazio.
    await db[logs.NAME].aggregate(pipeline)
