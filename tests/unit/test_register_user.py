"""Testes unitários de RegisterUser."""

import pytest

from app.application.errors import Conflict
from app.application.use_cases.users.register_user import RegisterUser
from tests.unit.conftest import CUSTOMER_ID, make_user, mock_user_repo


async def _execute(user_repo=None, **overrides):
    defaults = dict(
        customer_id=CUSTOMER_ID,
        name="Beltrano",
        email="beltrano@example.com",
        password="S3nh@F0rte!",
    )
    return await RegisterUser(user_repo or mock_user_repo()).execute(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_cadastro_valido_retorna_user():
    result = await _execute()
    assert result is not None


@pytest.mark.asyncio
async def test_email_ja_cadastrado_levanta_conflict():
    user_repo = mock_user_repo(by_email=make_user())
    with pytest.raises(Conflict):
        await _execute(user_repo=user_repo)


@pytest.mark.asyncio
async def test_senha_armazenada_como_hash():
    user_repo = mock_user_repo()
    await _execute(user_repo=user_repo)
    args, _ = user_repo.create.call_args
    # create(customer_id, name, email, password_hash)
    password_hash = args[3]
    assert password_hash != "S3nh@F0rte!"
    assert password_hash.startswith("$argon2")


@pytest.mark.asyncio
async def test_customer_id_repassado_ao_repositorio():
    user_repo = mock_user_repo()
    await _execute(user_repo=user_repo)
    args, _ = user_repo.create.call_args
    assert args[0] == CUSTOMER_ID
