"""Testes unitários de RegisterApplication."""

import pytest

from app.application.use_cases.applications.register_application import RegisterApplication
from tests.unit.conftest import CUSTOMER_ID, mock_app_repo


async def _execute(app_repo=None, **overrides):
    defaults = dict(customer_id=CUSTOMER_ID, name="minha-app", tags=[])
    return await RegisterApplication(app_repo or mock_app_repo()).execute(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_cadastro_valido_retorna_application():
    result = await _execute()
    assert result is not None


@pytest.mark.asyncio
async def test_tags_repassadas_ao_repositorio():
    app_repo = mock_app_repo()
    await _execute(app_repo=app_repo, tags=["env:prod", "region:us"])
    args, _ = app_repo.create.call_args
    # create(customer_id, name, tags)
    assert args[2] == ["env:prod", "region:us"]


@pytest.mark.asyncio
async def test_sem_tags_repassado_lista_vazia():
    app_repo = mock_app_repo()
    await _execute(app_repo=app_repo, tags=[])
    args, _ = app_repo.create.call_args
    assert args[2] == []


@pytest.mark.asyncio
async def test_customer_id_e_name_repassados():
    app_repo = mock_app_repo()
    await _execute(app_repo=app_repo, name="api-pagamentos")
    args, _ = app_repo.create.call_args
    assert args[0] == CUSTOMER_ID
    assert args[1] == "api-pagamentos"
