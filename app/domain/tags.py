"""Tipo compartilhado Tag: normaliza e valida o formato chave:valor (RN-15).

Usado por LogCreate e ApplicationCreate para garantir que a normalização e a
validação aconteçam no modelo Pydantic, não no use case.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, Field

from app.domain.constraints import MAX_TAGS, TAG_MAX_LENGTH, TAG_PATTERN

_TAG_RE = re.compile(TAG_PATTERN)


def _normalize(value: str) -> str:
    t = value.strip().lower()
    if not _TAG_RE.match(t):
        raise ValueError(f"Tag inválida: {value!r} — formato esperado chave:valor")
    if len(t) > TAG_MAX_LENGTH:
        raise ValueError(f"Tag muito longa: {value!r} — máximo {TAG_MAX_LENGTH} caracteres")
    return t


Tag = Annotated[str, AfterValidator(_normalize)]
