"""Testes unitários de LoginUser."""

import jwt
import pytest

from app.application.errors import Forbidden, NotAuthenticated
from app.application.use_cases.auth.login_user import LoginUser
from tests.unit.conftest import (
    JWT_SECRET,
    PASSWORD,
    make_customer,
    make_user,
    mock_customer_repo,
    mock_user_repo,
)


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)


def _make_user_repo():
    return mock_user_repo(by_email=make_user())


async def _execute(user_repo=None, customer_repo=None, email="fulano@example.com", password=PASSWORD):
    return await LoginUser(
        user_repo or _make_user_repo(),
        customer_repo or mock_customer_repo(),
    ).execute(email, password)


@pytest.mark.asyncio
async def test_login_valido_retorna_token():
    result = await _execute()
    assert result.token_type == "bearer"
    assert result.expires_in == 3600
    payload = jwt.decode(
        result.access_token, JWT_SECRET, algorithms=["HS256"],
        audience="user", options={"verify_exp": False},
    )
    assert payload["aud"] == "user"
    assert "customer_id" in payload


@pytest.mark.asyncio
async def test_email_nao_encontrado_levanta_not_authenticated():
    with pytest.raises(NotAuthenticated):
        await _execute(user_repo=mock_user_repo(by_email=None))


@pytest.mark.asyncio
async def test_senha_errada_levanta_not_authenticated():
    with pytest.raises(NotAuthenticated):
        await _execute(password="SenhaErrada!")


@pytest.mark.asyncio
async def test_cliente_inativo_levanta_forbidden():
    customer = make_customer(is_active=False)
    with pytest.raises(Forbidden):
        await _execute(customer_repo=mock_customer_repo(by_id=customer))


@pytest.mark.asyncio
async def test_cliente_nao_encontrado_levanta_forbidden():
    with pytest.raises(Forbidden):
        await _execute(customer_repo=mock_customer_repo(by_id=None))


@pytest.mark.asyncio
async def test_token_contem_sub_e_customer_id():
    user = make_user()
    result = await _execute(user_repo=mock_user_repo(by_email=user))
    payload = jwt.decode(
        result.access_token, JWT_SECRET, algorithms=["HS256"],
        audience="user", options={"verify_exp": False},
    )
    assert payload["sub"] == str(user.id)
    assert payload["customer_id"] == str(user.customer_id)
