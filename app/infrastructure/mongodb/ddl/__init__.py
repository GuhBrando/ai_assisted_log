"""Schema (DDL) do MongoDB: um módulo por coleção, aplicado por `app.infrastructure.mongodb.migrate`."""

from app.infrastructure.mongodb.ddl import (
    applications,
    customers,
    log_levels,
    log_metrics_hourly,
    logs,
    users,
)
from app.infrastructure.mongodb.ddl.spec import CollectionSpec

COLLECTIONS: tuple[CollectionSpec, ...] = (
    customers.SPEC,
    users.SPEC,
    applications.SPEC,
    log_levels.SPEC,
    logs.SPEC,
    log_metrics_hourly.SPEC,
)
