"""DDL de `users`: pessoas que acessam a plataforma de logs (RN-11).

A collation padrão da coleção ignora maiúsculas em toda comparação de texto: "Ana@Example.com" e
"ana@example.com" são o mesmo e-mail no índice único e no login, sem o backend passar collation
em cada consulta. O e-mail é gravado como foi digitado.
"""

from pymongo import ASCENDING, IndexModel
from pymongo.collation import Collation, CollationStrength

from app.infrastructure.mongodb.ddl.spec import CollectionSpec

NAME = "users"

COLLATION = Collation(locale="en", strength=CollationStrength.SECONDARY)

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "customerId", "name", "email", "passwordHash", "createdAt"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "customerId": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1},
            "email": {"bsonType": "string", "maxLength": 254, "pattern": r"^[^@\s]+@[^@\s]+$"},
            "passwordHash": {
                "bsonType": "string",
                "pattern": r"^\$argon2id\$",
                "description": "Hash pwdlib + Argon2id (ADR-007). Recusa senha em texto.",
            },
            "createdAt": {"bsonType": "date"},
        },
    }
}

INDEXES = (
    IndexModel([("email", ASCENDING)], name="users_email_unique", unique=True),
    IndexModel([("customerId", ASCENDING)], name="users_customer"),
)

SPEC = CollectionSpec(NAME, VALIDATOR, INDEXES, collation=COLLATION)
