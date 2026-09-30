"""Aplica o schema do MongoDB: coleções com validator, collation, índices e cargas iniciais.

Idempotente: cria o que falta, reaplica os validators e não mexe nos índices que já estão iguais.
Pode rodar a cada subida do ambiente e antes de cada deploy.

Uso: MONGODB_URI=mongodb://host:27017/log_api python -m app.infrastructure.mongodb.migrate
"""

import asyncio
import logging
import os
from typing import Any

from app.infrastructure.mongodb.client import MongoDatabase, create_mongo_client
from app.infrastructure.mongodb.ddl import COLLECTIONS
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

logger = logging.getLogger(__name__)

# strict: todo insert e update é validado; error: documento inválido é recusado, não só registrado.
_VALIDATION = {"validationLevel": "strict", "validationAction": "error"}


async def apply_schema(db: MongoDatabase) -> None:
    """Aplica todas as coleções em paralelo; nenhuma depende de outra."""
    existing = {info["name"]: info async for info in await db.list_collections()}
    async with asyncio.TaskGroup() as group:
        for spec in COLLECTIONS:
            group.create_task(_apply_collection(db, spec, existing.get(spec.name)))


async def _apply_collection(db: MongoDatabase, spec: CollectionSpec, info: dict[str, Any] | None) -> None:
    if info is None:
        options = {"collation": spec.collation} if spec.collation else {}
        await db.create_collection(
            spec.name, check_exists=False, validator=spec.validator, **_VALIDATION, **options
        )
        logger.info("%s: coleção criada", spec.name)
    else:
        _check_collation(spec, info)
        await db.command("collMod", spec.name, validator=spec.validator, **_VALIDATION)
        logger.info("%s: validator reaplicado", spec.name)

    collection = db[spec.name]
    if spec.indexes:
        names = await collection.create_indexes(list(spec.indexes))
        logger.info("%s: índices %s", spec.name, ", ".join(names))
    if spec.seed:
        await spec.seed(collection)
        logger.info("%s: carga inicial aplicada", spec.name)


def _check_collation(spec: CollectionSpec, info: dict[str, Any]) -> None:
    if spec.collation is None:
        return
    current = info.get("options", {}).get("collation", {})
    if any(current.get(key) != value for key, value in spec.collation.document.items()):
        raise RuntimeError(
            f"{spec.name}: a collation da coleção existente é {current or 'a padrão'}, mas o schema pede "
            f"{spec.collation.document}. O MongoDB não altera a collation de uma coleção: é preciso "
            "recriá-la e copiar os documentos."
        )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    client = create_mongo_client(os.environ["MONGODB_URI"])
    try:
        await apply_schema(client.get_default_database())
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
