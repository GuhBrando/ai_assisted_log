"""Testes unitários de QueryLogs."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from bson import ObjectId

from app.application.models import LogPage
from app.application.use_cases.logs.query_logs import QueryLogs
from tests.unit.conftest import CUSTOMER_ID, make_log, mock_log_repo


async def _execute(log_repo=None, **overrides):
    defaults = dict(customer_id=CUSTOMER_ID)
    return await QueryLogs(log_repo or mock_log_repo()).execute(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_retorna_pagina_com_items():
    result = await _execute()
    assert isinstance(result, LogPage)
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_limit_acima_de_100_e_truncado():
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, limit=999)
    _, kwargs = log_repo.list_by_customer.call_args
    assert kwargs["limit"] == 100


@pytest.mark.asyncio
async def test_limit_abaixo_de_1_e_elevado_para_1():
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, limit=0)
    _, kwargs = log_repo.list_by_customer.call_args
    assert kwargs["limit"] == 1


@pytest.mark.asyncio
async def test_limit_valido_repassado():
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, limit=25)
    _, kwargs = log_repo.list_by_customer.call_args
    assert kwargs["limit"] == 25


@pytest.mark.asyncio
async def test_filtros_repassados_ao_repositorio():
    app_id = ObjectId()
    cid = uuid4()
    from_date = datetime(2026, 1, 1, tzinfo=UTC)
    to_date = datetime(2026, 1, 31, tzinfo=UTC)
    log_repo = mock_log_repo()

    await _execute(
        log_repo=log_repo,
        application_id=app_id,
        level_min=3,
        correlation_id=cid,
        tags=["env:prod"],
        from_date=from_date,
        to_date=to_date,
        cursor="abc123",
    )

    _, kwargs = log_repo.list_by_customer.call_args
    assert kwargs["application_id"] == app_id
    assert kwargs["level_min"] == 3
    assert kwargs["correlation_id"] == cid
    assert kwargs["tags"] == ["env:prod"]
    assert kwargs["from_date"] == from_date
    assert kwargs["to_date"] == to_date
    assert kwargs["cursor"] == "abc123"


@pytest.mark.asyncio
async def test_tags_none_repassado_como_lista_vazia():
    log_repo = mock_log_repo()
    await _execute(log_repo=log_repo, tags=None)
    _, kwargs = log_repo.list_by_customer.call_args
    assert kwargs["tags"] == []


@pytest.mark.asyncio
async def test_pagina_vazia_retorna_items_vazio():
    log_repo = mock_log_repo(page=LogPage(items=[], next_cursor=None))
    result = await _execute(log_repo=log_repo)
    assert result.items == []
    assert result.next_cursor is None


@pytest.mark.asyncio
async def test_next_cursor_presente_quando_ha_mais():
    page = LogPage(items=[make_log()], next_cursor="cursor_opaco")
    log_repo = mock_log_repo(page=page)
    result = await _execute(log_repo=log_repo)
    assert result.next_cursor == "cursor_opaco"
