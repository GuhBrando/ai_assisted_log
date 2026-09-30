from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pymongo import IndexModel
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.collation import Collation

type Seed = Callable[[AsyncCollection[dict[str, Any]]], Awaitable[None]]


@dataclass(frozen=True)
class CollectionSpec:
    """DDL de uma coleção: validator, índices e, quando houver, collation padrão e carga inicial.

    A collation padrão só é definida na criação; o MongoDB não permite alterá-la depois.
    """

    name: str
    validator: dict[str, Any]
    indexes: tuple[IndexModel, ...] = ()
    collation: Collation | None = None
    seed: Seed | None = None
