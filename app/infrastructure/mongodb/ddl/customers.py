"""DDL de `customers`: empresa cliente e dimensão Cliente do modelo dimensional (ADR-021)."""

from app.domain.constraints import RETENTION_DAYS_MAX, RETENTION_DAYS_MIN
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

NAME = "customers"

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "name", "isActive", "retentionDays", "createdAt"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1},
            "isActive": {"bsonType": "bool"},
            "retentionDays": {
                "bsonType": "int",
                "minimum": RETENTION_DAYS_MIN,
                "maximum": RETENTION_DAYS_MAX,
                "description": "Por quantos dias os logs do cliente ficam guardados (RN-08).",
            },
            "createdAt": {"bsonType": "date"},
        },
    }
}

# Só há leituras por _id (credencial e /customers/me): o índice padrão basta.
SPEC = CollectionSpec(NAME, VALIDATOR)
