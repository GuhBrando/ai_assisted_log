"""Testes unitários de RegisterCustomer."""

import pytest
from fastapi import HTTPException

from app.application.errors import Conflict
from app.application.use_cases.customers.register_customer import RegisterCustomer
from tests.unit.conftest import make_user, mock_customer_repo, mock_user_repo

_BASE = dict(
    customer_name="Acme Corp",
    retention_days=30,
    user_name="Admin",
    user_email="admin@acme.com",
    user_password="S3nh@F0rte!",
)


async def _execute(user_repo=None, customer_repo=None, **overrides):
    use_case = RegisterCustomer(
        customer_repo or mock_customer_repo(),
        user_repo or mock_user_repo(),
    )
    return await use_case.execute(**{**_BASE, **overrides})


@pytest.mark.asyncio
async def test_cadastro_valido_retorna_customer_e_user():
    result = await _execute()
    assert result.customer is not None
    assert result.user is not None


@pytest.mark.asyncio
async def test_email_ja_cadastrado_levanta_conflict():
    user_repo = mock_user_repo(by_email=make_user())
    with pytest.raises(Conflict):
        await _execute(user_repo=user_repo)


@pytest.mark.asyncio
async def test_retention_days_abaixo_do_minimo_levanta_422():
    with pytest.raises(HTTPException) as exc:
        await _execute(retention_days=0)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_retention_days_acima_do_maximo_levanta_422():
    with pytest.raises(HTTPException) as exc:
        await _execute(retention_days=9999)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_retention_days_no_limite_minimo_valido():
    result = await _execute(retention_days=1)
    assert result.customer is not None


@pytest.mark.asyncio
async def test_retention_days_no_limite_maximo_valido():
    result = await _execute(retention_days=3650)
    assert result.customer is not None


@pytest.mark.asyncio
async def test_senha_armazenada_como_hash():
    user_repo = mock_user_repo()
    await _execute(user_repo=user_repo)
    args, _ = user_repo.create.call_args
    # create(customer_id, name, email, password_hash)
    password_hash = args[3]
    assert password_hash != "S3nh@F0rte!"
    assert password_hash.startswith("$argon2")
