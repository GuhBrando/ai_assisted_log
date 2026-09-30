"""Schemas de campo usados em mais de uma coleção."""

from typing import Any

from app.domain.constraints import TAG_MAX_LENGTH, TAG_PATTERN
from app.domain.log_level import LogLevel

LEVEL: dict[str, Any] = {
    "bsonType": "int",
    "enum": [int(level) for level in LogLevel],
    "description": "Valor numérico de LogLevel (ADR-011).",
}


def tag_list(max_items: int) -> dict[str, Any]:
    """Tags já normalizadas, `chave:valor` em minúsculas e sem repetição (RN-15)."""
    return {
        "bsonType": "array",
        "maxItems": max_items,
        "uniqueItems": True,
        "items": {"bsonType": "string", "maxLength": TAG_MAX_LENGTH, "pattern": TAG_PATTERN},
    }
