"""Testes das rotas do painel com os nomes e formatos do contrato, como o frontend desktop chama."""

from datetime import UTC, datetime, timedelta

import pytest

_LOG_READ_FIELDS = {
    "id",
    "application_id",
    "application_name",
    "correlation_id",
    "level",
    "message",
    "exception",
    "environment",
    "information_data",
    "tags",
    "occurred_at",
    "received_at",
    "expire_at",
}


async def _setup_panel(http_client, suffix: str):
    """Helper: cria cliente → aplicação → API key e devolve os tokens de usuário e de aplicação."""
    r = await http_client.post("/customers", json={
        "name": f"PanelCo{suffix}",
        "retention_days": 7,
        "user_name": "Dev",
        "user_email": f"panel{suffix}@panelco.com",
        "user_password": "devpass123",
    })
    assert r.status_code == 201, r.text

    r = await http_client.post("/auth/login", json={
        "email": f"panel{suffix}@panelco.com",
        "password": "devpass123",
    })
    user_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await http_client.post(
        "/applications", headers=user_headers, json={"name": "Checkout", "tags": ["team:checkout"]}
    )
    app_id = r.json()["id"]

    r = await http_client.post(f"/applications/{app_id}/api-keys", headers=user_headers, json={})
    r = await http_client.post("/auth/token", headers={"X-API-Key": r.json()["raw_key"]})
    app_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return user_headers, app_headers, app_id


@pytest.mark.asyncio
async def test_list_applications_contract_shape(http_client):
    user_headers, _, app_id = await _setup_panel(http_client, "1")

    r = await http_client.get("/applications", headers=user_headers)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [a["id"] for a in items] == [app_id]
    assert set(items[0]) == {"id", "name", "tags", "api_keys", "created_at"}
    assert items[0]["tags"] == ["team:checkout"]
    # A chave sai sem o segredo e sem o hash
    assert len(items[0]["api_keys"]) == 1
    assert set(items[0]["api_keys"][0]) == {"prefix", "expires_at", "revoked_at"}


@pytest.mark.asyncio
async def test_list_logs_contract_filters(http_client):
    user_headers, app_headers, app_id = await _setup_panel(http_client, "2")
    t0 = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    for minute, level in [(0, 1), (10, 3), (20, 4)]:
        r = await http_client.post("/logs", headers=app_headers, json={
            "level": level,
            "message": f"Log {level}",
            "environment": "production",
            "occurred_at": (t0 + timedelta(minutes=minute)).isoformat(),
        })
        assert r.status_code == 201, r.text

    async def levels(**params) -> list[int]:
        r = await http_client.get("/logs", headers=user_headers, params=params)
        assert r.status_code == 200, r.text
        return [log["level"] for log in r.json()["items"]]

    assert await levels() == [4, 3, 1]
    assert await levels(min_level=3) == [4, 3]
    assert await levels(application_id=app_id) == [4, 3, 1]
    # Início inclusivo, fim exclusivo
    assert await levels(
        occurred_from=(t0 + timedelta(minutes=10)).isoformat(),
        occurred_to=(t0 + timedelta(minutes=20)).isoformat(),
    ) == [3]

    r = await http_client.get("/logs", headers=user_headers)
    log = r.json()["items"][0]
    assert set(log) == _LOG_READ_FIELDS
    r = await http_client.get(f"/logs/{log['id']}", headers=user_headers)
    assert set(r.json()) == _LOG_READ_FIELDS


@pytest.mark.asyncio
async def test_list_logs_invalid_application_id(http_client):
    user_headers, _, _ = await _setup_panel(http_client, "3")

    r = await http_client.get("/logs", headers=user_headers, params={"application_id": "abc"})
    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"
