"""Testes unitários de RevokeApiKey."""

import pytest
from bson import ObjectId

from app.application.errors import NotFound
from app.application.use_cases.applications.revoke_api_key import RevokeApiKey
from tests.unit.conftest import APP_ID, CUSTOMER_ID, make_application, mock_app_repo


async def _execute(app_repo=None, **overrides):
    defaults = dict(customer_id=CUSTOMER_ID, app_id=APP_ID, prefix="lx_testapikey1")
    return await RevokeApiKey(app_repo or mock_app_repo()).execute(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_revoga_chave_existente():
    await _execute()  # não levanta


@pytest.mark.asyncio
async def test_aplicacao_nao_encontrada_levanta_not_found():
    with pytest.raises(NotFound):
        await _execute(app_repo=mock_app_repo(by_id=None))


@pytest.mark.asyncio
async def test_aplicacao_de_outro_cliente_levanta_not_found():
    app = make_application(customer_id=ObjectId())
    with pytest.raises(NotFound):
        await _execute(app_repo=mock_app_repo(by_id=app))


@pytest.mark.asyncio
async def test_chave_nao_encontrada_levanta_not_found():
    app_repo = mock_app_repo(revoked=False)
    with pytest.raises(NotFound):
        await _execute(app_repo=app_repo)
