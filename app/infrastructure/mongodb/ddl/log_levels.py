"""DDL de `log_levels`: dimensão Nível do modelo dimensional (ADR-021).

Carregada a partir de `LogLevel`, que continua sendo a fonte da verdade: o backend usa o enum e
não lê esta coleção. Ela existe para quem consulta o banco fora do Python (BI, Compass, mongosh)
traduzir `level` em nome sem conhecer o código.
"""

from typing import Any

from pymongo import ReplaceOne
from pymongo.asynchronous.collection import AsyncCollection

from app.domain.log_level import LogLevel
from app.infrastructure.mongodb.ddl.fields import LEVEL
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

NAME = "log_levels"

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "name"],
        "properties": {
            "_id": LEVEL,
            "name": {"bsonType": "string", "enum": [level.name for level in LogLevel]},
        },
    }
}


async def seed(collection: AsyncCollection[dict[str, Any]]) -> None:
    """Deixa a coleção igual ao enum: um documento por nível, sem sobras."""
    levels = [int(level) for level in LogLevel]
    await collection.bulk_write(
        [ReplaceOne({"_id": int(level)}, {"name": level.name}, upsert=True) for level in LogLevel]
    )
    await collection.delete_many({"_id": {"$nin": levels}})


SPEC = CollectionSpec(NAME, VALIDATOR, seed=seed)
