"""Testes unitários de ApiKeyDoc.is_valid."""

from datetime import UTC, datetime, timedelta

import pytest

from app.application.models import ApiKeyDoc

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _key(expires_at=None, revoked_at=None) -> ApiKeyDoc:
    return ApiKeyDoc(
        key_hash="abc",
        prefix="lx_abc",
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def test_valid_sem_expiracao():
    assert _key().is_valid(NOW) is True


def test_valid_expiracao_futura():
    assert _key(expires_at=NOW + timedelta(seconds=1)).is_valid(NOW) is True


def test_invalido_expirado_exatamente_no_limite():
    # expires_at == now → inválido (limite exclusivo)
    assert _key(expires_at=NOW).is_valid(NOW) is False


def test_invalido_expirado_no_passado():
    assert _key(expires_at=NOW - timedelta(seconds=1)).is_valid(NOW) is False


def test_invalido_revogado_exatamente_no_limite():
    assert _key(revoked_at=NOW).is_valid(NOW) is False


def test_invalido_revogado_no_passado():
    assert _key(revoked_at=NOW - timedelta(hours=1)).is_valid(NOW) is False


def test_valido_revogado_no_futuro():
    # revoked_at > now significa que a revogação ainda não "ocorreu" na timeline
    assert _key(revoked_at=NOW + timedelta(seconds=1)).is_valid(NOW) is True


def test_invalido_revogado_e_expirado():
    assert _key(
        expires_at=NOW - timedelta(hours=1),
        revoked_at=NOW - timedelta(hours=2),
    ).is_valid(NOW) is False
