"""DDL de `logs`: o fato do modelo dimensional, um documento por evento (ADR-021).

- Só a API grava, com `insert_one`; quem apaga é o TTL em `expireAt` (ADR-004, ADR-013).
- Todos os campos são gravados; opcional sem valor vai como null. Todo documento tem o mesmo formato.
- Todo índice de consulta começa por `customerId` (RN-09) e termina em `(occurredAt, _id)`:
  o `_id` desempata logs com o mesmo `occurredAt` na paginação por cursor.
- Filtro de nível vai como `$in` com os níveis da faixa, não `$gte`: com `$in` o MongoDB junta
  os trechos do índice já ordenados; com `$gte` ele ordena em memória.
"""

from bson.binary import Binary
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.domain.constraints import MAX_LOG_TAGS, RETENTION_DAYS_MAX, RETENTION_DAYS_MIN
from app.infrastructure.mongodb.ddl.fields import LEVEL, tag_list
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

NAME = "logs"

DAY_MS = 86_400_000

_retention_ms = {"$subtract": ["$expireAt", "$receivedAt"]}

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "customerId",
            "applicationId",
            "applicationName",
            "correlationId",
            "level",
            "message",
            "exception",
            "environment",
            "informationData",
            "tags",
            "occurredAt",
            "receivedAt",
            "expireAt",
        ],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "customerId": {"bsonType": "objectId"},
            "applicationId": {"bsonType": "objectId"},
            "applicationName": {
                "bsonType": "string",
                "minLength": 1,
                "description": "Cópia de applications.name na gravação (ADR-003).",
            },
            "correlationId": {
                "bsonType": ["binData", "null"],
                "description": "UUID gravado como binData subtipo 4 (uuidRepresentation=standard).",
            },
            "level": LEVEL,
            "message": {"bsonType": "string", "minLength": 1},
            "exception": {"bsonType": ["string", "null"]},
            "environment": {"bsonType": "string", "minLength": 1},
            "informationData": {
                "bsonType": ["object", "null"],
                "description": "Livre, já mascarado. Tamanho e chaves com $ ou . são checados na API.",
            },
            "tags": tag_list(MAX_LOG_TAGS),
            "occurredAt": {"bsonType": "date"},
            "receivedAt": {"bsonType": "date"},
            "expireAt": {"bsonType": "date"},
        },
    },
    # expireAt = receivedAt + retentionDays (RN-08). Pega, por exemplo, a retenção somada em
    # segundos em vez de dias, que apagaria o log logo depois de gravado.
    "$expr": {
        "$and": [
            {"$gte": [_retention_ms, RETENTION_DAYS_MIN * DAY_MS]},
            {"$lte": [_retention_ms, RETENTION_DAYS_MAX * DAY_MS]},
        ]
    },
}

_BY_TIME = [("occurredAt", DESCENDING), ("_id", DESCENDING)]

INDEXES = (
    IndexModel([("customerId", ASCENDING), *_BY_TIME], name="logs_customer_occurred"),
    IndexModel(
        [("customerId", ASCENDING), ("level", ASCENDING), *_BY_TIME],
        name="logs_customer_level_occurred",
    ),
    IndexModel(
        [("customerId", ASCENDING), ("applicationId", ASCENDING), ("level", ASCENDING), *_BY_TIME],
        name="logs_customer_application_level_occurred",
    ),
    IndexModel(
        [("customerId", ASCENDING), ("correlationId", ASCENDING), *_BY_TIME],
        name="logs_customer_correlation_occurred",
        # Só logs com correlationId: o filtro é o menor binData possível, então null fica de fora.
        # Com {"$type": "binData"} o MongoDB não usa o índice na busca por um UUID.
        partialFilterExpression={"correlationId": {"$gte": Binary(b"")}},
    ),
    IndexModel(
        [("customerId", ASCENDING), ("tags", ASCENDING), *_BY_TIME],
        name="logs_customer_tags_occurred",
    ),
    IndexModel([("expireAt", ASCENDING)], name="logs_expire_ttl", expireAfterSeconds=0),
)

SPEC = CollectionSpec(NAME, VALIDATOR, INDEXES)
