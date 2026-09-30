from enum import IntEnum


class LogLevel(IntEnum):
    """Severidade do log, gravada como número (ADR-011). Filtrar a partir de um nível é `level >= nível`."""

    TRACE = 0
    DEBUG = 1
    INFORMATION = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5
