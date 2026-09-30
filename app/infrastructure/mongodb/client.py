from datetime import UTC
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

type MongoDatabase = AsyncDatabase[dict[str, Any]]


def create_mongo_client(uri: str, **kwargs: Any) -> AsyncMongoClient[dict[str, Any]]:
    """Cria o cliente do MongoDB. API, migração e testes usam só esta função, com as mesmas opções de codec.

    - `uuidRepresentation="standard"`: `uuid.UUID` vira binData subtipo 4 e volta como `uuid.UUID`.
      Sem ela, gravar um UUID falha e ler devolve `bson.Binary`.
    - `tz_aware=True` com `tzinfo=UTC`: as datas voltam com fuso UTC, nunca sem fuso.
    """
    return AsyncMongoClient(uri, uuidRepresentation="standard", tz_aware=True, tzinfo=UTC, **kwargs)
