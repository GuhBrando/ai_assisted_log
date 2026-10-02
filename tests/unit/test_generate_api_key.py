"""Testes unitários de GenerateApiKey."""

import pytest

from app.application.errors import NotFound
from app.application.use_cases.applications.generate_api_key import GenerateApiKey
from tests.unit.conftest import APP_ID, CUSTOMER_ID, make_application, mock_app_repo
from bson import ObjectId


async def _execute(app_repo=None, **overrides):
    defaults = dict(customer_id=CUSTOMER_ID, app_id=APP_ID, expires_at=None)
    return await GenerateApiKey(app_repo or mock_app_repo()).execute(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_gera_chave_com_prefixo_lx():
    result = await _execute()
    assert result.raw_key.startswith("lx_")


@pytest.mark.asyncio
async def test_prefixo_tem_10_caracteres():
    result = await _execute()
    assert len(result.prefix) == 10


@pytest.mark.asyncio
async def test_prefix_e_inicio_da_raw_key():
    result = await _execute()
    assert result.raw_key.startswith(result.prefix)


@pytest.mark.asyncio
async def test_chave_bruta_diferente_a_cada_chamada():
    result1 = await _execute()
    result2 = await _execute()
    assert result1.raw_key != result2.raw_key


@pytest.mark.asyncio
async def test_aplicacao_nao_encontrada_levanta_not_found():
    with pytest.raises(NotFound):
        await _execute(app_repo=mock_app_repo(by_id=None))


@pytest.mark.asyncio
async def test_aplicacao_de_outro_cliente_levanta_not_found():
    outro_customer = ObjectId()
    app = make_application(customer_id=outro_customer)
    with pytest.raises(NotFound):
        await _execute(app_repo=mock_app_repo(by_id=app))


@pytest.mark.asyncio
async def test_hash_adicionado_ao_repositorio():
    import hashlib
    app_repo = mock_app_repo()
    result = await _execute(app_repo=app_repo)
    args, _ = app_repo.add_api_key.call_args
    # add_api_key(app_id, key_hash, prefix, expires_at)
    expected_hash = hashlib.sha256(result.raw_key.encode()).hexdigest()
    assert args[1] == expected_hash


@pytest.mark.asyncio
async def test_expires_at_repassado_ao_repositorio():
    from datetime import UTC, datetime, timedelta
    expires = datetime.now(UTC) + timedelta(days=30)
    app_repo = mock_app_repo()
    result = await _execute(app_repo=app_repo, expires_at=expires)
    assert result.expires_at == expires
    args, _ = app_repo.add_api_key.call_args
    assert args[3] == expires
