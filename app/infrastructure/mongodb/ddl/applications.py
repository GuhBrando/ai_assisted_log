"""DDL de `applications`: sistemas do cliente, com as API keys embutidas (ADR-003, ADR-008).

- `apiKeys.keyHash` é único entre aplicações. O índice é parcial porque a aplicação nasce sem
  chaves: num índice único comum, duas aplicações sem chave colidem no valor nulo.
- O nome é único dentro do cliente, sem diferenciar maiúsculas (409). A collation fica só nesse
  índice, e não na coleção, para a busca por `keyHash` continuar diferenciando maiúsculas.
- Índice único não vale dentro de um mesmo documento: prefixo único na aplicação é garantido
  pelo backend no `$push` (filtro `"apiKeys.prefix": {"$ne": prefixo}`).
"""

from pymongo import ASCENDING, IndexModel
from pymongo.collation import Collation, CollationStrength

from app.domain.constraints import MAX_TAGS
from app.infrastructure.mongodb.ddl.fields import tag_list
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

NAME = "applications"

# Consultas por nome precisam passar esta collation para usar o índice.
NAME_COLLATION = Collation(locale="en", strength=CollationStrength.SECONDARY)

API_KEY = {
    "bsonType": "object",
    "additionalProperties": False,
    "required": ["keyHash", "prefix", "expiresAt", "revokedAt"],
    "properties": {
        "keyHash": {
            "bsonType": "string",
            "minLength": 1,
            "description": "Hash determinístico da chave (ADR-008). A chave nunca é gravada.",
        },
        "prefix": {"bsonType": "string", "minLength": 1},
        "expiresAt": {"bsonType": ["date", "null"]},
        "revokedAt": {"bsonType": ["date", "null"]},
    },
}

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "customerId", "name", "apiKeys", "tags", "createdAt"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "customerId": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1},
            "apiKeys": {"bsonType": "array", "items": API_KEY},
            "tags": tag_list(MAX_TAGS),
            "createdAt": {"bsonType": "date"},
        },
    }
}

INDEXES = (
    IndexModel(
        [("apiKeys.keyHash", ASCENDING)],
        name="applications_apiKeys_keyHash_unique",
        unique=True,
        partialFilterExpression={"apiKeys.keyHash": {"$exists": True}},
    ),
    IndexModel(
        [("customerId", ASCENDING), ("name", ASCENDING)],
        name="applications_customer_name_unique",
        unique=True,
        collation=NAME_COLLATION,
    ),
)

SPEC = CollectionSpec(NAME, VALIDATOR, INDEXES)
