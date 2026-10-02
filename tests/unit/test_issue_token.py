"""Testes unitários de IssueToken."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from app.application.errors import Forbidden, NotAuthenticated
from app.application.use_cases.auth.issue_token import IssueToken
from tests.unit.conftest import (
    JWT_SECRET,
    NOW,
    RAW_KEY,
    make_api_key,
    make_application,
    make_customer,
    mock_app_repo,
    mock_customer_repo,
)


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)


async def _execute(app_repo, customer_repo, raw_key=RAW_KEY):
    use_case = IssueToken(app_repo, customer_repo)
    with patch("app.application.use_cases.auth.issue_token.datetime") as mock_dt:
        mock_dt.now.return_value = NOW
        return await use_case.execute(raw_key)


@pytest.mark.asyncio
async def test_emite_token_com_chave_valida():
    result = await _execute(mock_app_repo(), mock_customer_repo())
    assert result.token_type == "bearer"
    assert result.expires_in == 3600
    # NOW é fixo no passado; desabilita verificação de exp para inspecionar o payload
    payload = jwt.decode(
        result.access_token, JWT_SECRET, algorithms=["HS256"],
        options={"verify_exp": False},
    )
    assert "sub" in payload
    assert "jti" in payload


@pytest.mark.asyncio
async def test_chave_nao_encontrada_levanta_not_authenticated():
    app_repo = mock_app_repo(by_hash=None)
    with pytest.raises(NotAuthenticated):
        await _execute(app_repo, mock_customer_repo())


@pytest.mark.asyncio
async def test_chave_revogada_levanta_not_authenticated():
    key = make_api_key(revoked_at=NOW - timedelta(minutes=1))
    app = make_application(api_keys=[key])
    app_repo = mock_app_repo(by_hash=app, by_id=app)
    with pytest.raises(NotAuthenticated):
        await _execute(app_repo, mock_customer_repo())


@pytest.mark.asyncio
async def test_chave_expirada_levanta_not_authenticated():
    key = make_api_key(expires_at=NOW - timedelta(seconds=1))
    app = make_application(api_keys=[key])
    app_repo = mock_app_repo(by_hash=app, by_id=app)
    with pytest.raises(NotAuthenticated):
        await _execute(app_repo, mock_customer_repo())


@pytest.mark.asyncio
async def test_cliente_inativo_levanta_forbidden():
    customer = make_customer(is_active=False)
    with pytest.raises(Forbidden):
        await _execute(mock_app_repo(), mock_customer_repo(by_id=customer))


@pytest.mark.asyncio
async def test_cliente_nao_encontrado_levanta_forbidden():
    with pytest.raises(Forbidden):
        await _execute(mock_app_repo(), mock_customer_repo(by_id=None))


@pytest.mark.asyncio
async def test_exp_limitado_por_expires_at_da_chave():
    # Chave expira em 30 min — exp deve ser 30 min, não 1 hora
    expires_at = NOW + timedelta(minutes=30)
    key = make_api_key(expires_at=expires_at)
    app = make_application(api_keys=[key])
    app_repo = mock_app_repo(by_hash=app, by_id=app)

    result = await _execute(app_repo, mock_customer_repo())
    assert result.expires_in == 30 * 60


@pytest.mark.asyncio
async def test_exp_padrao_1_hora_quando_chave_nao_expira():
    key = make_api_key(expires_at=None)
    app = make_application(api_keys=[key])
    app_repo = mock_app_repo(by_hash=app, by_id=app)

    result = await _execute(app_repo, mock_customer_repo())
    assert result.expires_in == 3600
