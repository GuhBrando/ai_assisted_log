"""Testes unitários de IngestLog."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.application.errors import Forbidden, NotAuthenticated, PayloadTooLarge
from app.application.use_cases.logs.ingest_log import IngestLog
from tests.unit.conftest import (
    APP_ID,
    NOW,
    make_application,
    make_customer,
    mock_app_repo,
    mock_customer_repo,
    mock_log_repo,
)

_BASE = dict(
    app_id_str=str(APP_ID),
    correlation_id=None,
    level=2,
    message="mensagem de teste",
    exception=None,
    environment="prod",
    information_data=None,
    tags=[],
    occurred_at=NOW,
)


async def _execute(app_repo=None, customer_repo=None, log_repo=None, **overrides):
    use_case = IngestLog(
        app_repo or mock_app_repo(),
        customer_repo or mock_customer_repo(),
        log_repo or mock_log_repo(),
    )
    kwargs = {**_BASE, **overrides}
    return await use_case.execute(**kwargs)


@pytest.mark.asyncio
async def test_log_valido_retorna_object_id():
    from bson import ObjectId
    result = await _execute()
    assert isinstance(result, ObjectId)


@pytest.mark.asyncio
async def test_aplicacao_nao_encontrada_levanta_not_authenticated():
    with pytest.raises(NotAuthenticated):
        await _execute(app_repo=mock_app_repo(by_id=None))


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
async def test_mascara_campo_senha():
    log_repo = mock_log_repo()
    await _execute(
        log_repo=log_repo,
        information_data={"user": "joao", "password": "secret123"},
    )
    _, kwargs = log_repo.insert.call_args
    assert kwargs["information_data"]["password"] == "***REDACTED***"
    assert kwargs["information_data"]["user"] == "joao"


@pytest.mark.asyncio
async def test_mascara_campo_cpf():
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, information_data={"cpf": "123.456.789-00"})
    _, kwargs = log_repo.insert.call_args
    assert kwargs["information_data"]["cpf"] == "***REDACTED***"


@pytest.mark.asyncio
async def test_mascara_todos_campos_sensiveis():
    sensiveis = ["password", "senha", "cpf", "card", "credit_card", "creditcard",
                 "cvv", "ssn", "token", "secret", "api_key", "apikey", "pin"]
    log_repo = mock_log_repo()
    data = {campo: "valor" for campo in sensiveis}
    await _execute(log_repo=log_repo, information_data=data)
    _, kwargs = log_repo.insert.call_args
    for campo in sensiveis:
        assert kwargs["information_data"][campo] == "***REDACTED***"


@pytest.mark.asyncio
async def test_mascara_campo_sensivel_aninhado():
    log_repo = mock_log_repo()
    await _execute(
        log_repo=log_repo,
        information_data={"usuario": {"nome": "joao", "token": "abc123"}},
    )
    _, kwargs = log_repo.insert.call_args
    assert kwargs["information_data"]["usuario"]["token"] == "***REDACTED***"
    assert kwargs["information_data"]["usuario"]["nome"] == "joao"


@pytest.mark.asyncio
async def test_chave_com_dolar_levanta_422():
    with pytest.raises(HTTPException) as exc:
        await _execute(information_data={"$where": "malicioso"})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_chave_com_ponto_levanta_422():
    with pytest.raises(HTTPException) as exc:
        await _execute(information_data={"chave.proibida": "valor"})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_chave_proibida_aninhada_levanta_422():
    with pytest.raises(HTTPException) as exc:
        await _execute(information_data={"nivel1": {"$operador": "valor"}})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_information_data_acima_64kb_levanta_payload_too_large():
    grande = {"k": "x" * 70_000}
    with pytest.raises(PayloadTooLarge):
        await _execute(information_data=grande)


@pytest.mark.asyncio
async def test_tags_da_aplicacao_tem_precedencia():
    # Aplicação tem "env:prod"; log envia "env:staging" → deve prevalecer "env:prod"
    app = make_application(tags=["env:prod"])
    log_repo = mock_log_repo()
    await _execute(
        app_repo=mock_app_repo(by_id=app),
        log_repo=log_repo,
        tags=["env:staging", "version:1.0"],
    )
    _, kwargs = log_repo.insert.call_args
    tags = kwargs["tags"]
    assert "env:prod" in tags
    assert "env:staging" not in tags
    assert "version:1.0" in tags


@pytest.mark.asyncio
async def test_tags_da_aplicacao_mescladas_com_tags_do_log():
    app = make_application(tags=["region:us"])
    log_repo = mock_log_repo()
    await _execute(
        app_repo=mock_app_repo(by_id=app),
        log_repo=log_repo,
        tags=["version:2.0"],
    )
    _, kwargs = log_repo.insert.call_args
    tags = kwargs["tags"]
    assert "region:us" in tags
    assert "version:2.0" in tags


@pytest.mark.asyncio
async def test_expire_at_calculado_com_retention_days():
    customer = make_customer(retention_days=7)
    log_repo = mock_log_repo()
    await _execute(
        customer_repo=mock_customer_repo(by_id=customer),
        log_repo=log_repo,
    )
    _, kwargs = log_repo.insert.call_args
    delta = kwargs["expire_at"] - kwargs["received_at"]
    assert delta.days == 7


@pytest.mark.asyncio
async def test_correlation_id_repassado_ao_repositorio():
    cid = uuid4()
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, correlation_id=cid)
    _, kwargs = log_repo.insert.call_args
    assert kwargs["correlation_id"] == cid


@pytest.mark.asyncio
async def test_information_data_none_nao_mascara():
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, information_data=None)
    _, kwargs = log_repo.insert.call_args
    assert kwargs["information_data"] is None
