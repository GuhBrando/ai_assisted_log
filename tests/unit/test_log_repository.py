"""Testes auxiliares de serialização do cursor de logs."""

import base64
import json
from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.infrastructure.mongodb.repositories.log_repository import _decode_cursor, _encode_cursor


def test_cursor_valido_preserva_data_e_id():
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
    log_id = ObjectId()

    assert _decode_cursor(_encode_cursor(occurred_at, log_id)) == (occurred_at, log_id)


@pytest.mark.parametrize(
    "cursor",
    [
        "not-a-cursor",
        base64.urlsafe_b64encode(b"[]").decode(),
        base64.urlsafe_b64encode(b"{}").decode(),
        base64.urlsafe_b64encode(
            json.dumps({"occurred_at": "2026-01-01T00:00:00+00:00", "id": "invalid"}).encode()
        ).decode(),
    ],
)
def test_cursor_invalido_retorna_none(cursor: str):
    assert _decode_cursor(cursor) is None
