"""Testes do endpoint de ingestão e consulta de logs."""

from datetime import UTC, datetime

import pytest


async def _setup_app_token(http_client, suffix: str = ""):
    """Helper: cria cliente → aplicação → API key → token de aplicação."""
    r = await http_client.post("/customers", json={
        "name": f"LogCo{suffix}",
        "retention_days": 7,
        "user_name": "Dev",
        "user_email": f"dev{suffix}@logco.com",
        "user_password": "devpass123",
    })
    assert r.status_code == 201

    r = await http_client.post("/auth/login", json={
        "email": f"dev{suffix}@logco.com",
        "password": "devpass123",
    })
    user_token = r.json()["access_token"]

    r = await http_client.post(
        "/applications",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"name": "MyApp", "tags": ["team:backend"]},
    )
    app_id = r.json()["id"]

    r = await http_client.post(
        f"/applications/{app_id}/api-keys",
        headers={"Authorization": f"Bearer {user_token}"},
        json={},
    )
    raw_key = r.json()["raw_key"]

    r = await http_client.post("/auth/token", headers={"X-API-Key": raw_key})
    return r.json()["access_token"], user_token


@pytest.mark.asyncio
async def test_ingest_log_valid(http_client):
    app_token, _ = await _setup_app_token(http_client, suffix="1")

    r = await http_client.post(
        "/logs",
        headers={"Authorization": f"Bearer {app_token}"},
        json={
            "level": 2,
            "message": "Pedido criado",
            "environment": "production",
            "occurred_at": datetime.now(UTC).isoformat(),
            "tags": ["feature:pix"],
        },
    )
    assert r.status_code == 201, r.text
    assert "id" in r.json()


@pytest.mark.asyncio
async def test_ingest_log_sensitive_masking(http_client):
    app_token, user_token = await _setup_app_token(http_client, suffix="2")

    r = await http_client.post(
        "/logs",
        headers={"Authorization": f"Bearer {app_token}"},
        json={
            "level": 3,
            "message": "Tentativa de pagamento",
            "environment": "production",
            "occurred_at": datetime.now(UTC).isoformat(),
            "information_data": {
                "user": "ana",
                "password": "secreta123",
                "cpf": "123.456.789-00",
            },
        },
    )
    assert r.status_code == 201, r.text
    log_id = r.json()["id"]

    # Busca o log para verificar mascaramento
    r = await http_client.get(
        f"/logs/{log_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    info = r.json()["information_data"]
    assert info["password"] == "***REDACTED***"
    assert info["cpf"] == "***REDACTED***"
    assert info["user"] == "ana"


@pytest.mark.asyncio
async def test_ingest_log_no_token(http_client):
    r = await http_client.post(
        "/logs",
        json={
            "level": 2,
            "message": "Sem token",
            "environment": "test",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_log_invalid_level(http_client):
    app_token, _ = await _setup_app_token(http_client, suffix="3")

    r = await http_client.post(
        "/logs",
        headers={"Authorization": f"Bearer {app_token}"},
        json={
            "level": 9,
            "message": "Nível inválido",
            "environment": "test",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_ingest_log_forbidden_field(http_client):
    r = await http_client.post(
        "/logs",
        headers={"Authorization": "Bearer fake"},
        json={
            "level": 2,
            "message": "Com customer_id",
            "environment": "test",
            "occurred_at": datetime.now(UTC).isoformat(),
            "customer_id": "abc123",
        },
    )
    assert r.status_code in (401, 422)


@pytest.mark.asyncio
async def test_ingest_log_tags_merged(http_client):
    app_token, user_token = await _setup_app_token(http_client, suffix="4")

    r = await http_client.post(
        "/logs",
        headers={"Authorization": f"Bearer {app_token}"},
        json={
            "level": 2,
            "message": "Com tags",
            "environment": "production",
            "occurred_at": datetime.now(UTC).isoformat(),
            "tags": ["feature:checkout"],
        },
    )
    assert r.status_code == 201
    log_id = r.json()["id"]

    r = await http_client.get(
        f"/logs/{log_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tags = r.json()["tags"]
    # "team:backend" da aplicação + "feature:checkout" do log
    assert "team:backend" in tags
    assert "feature:checkout" in tags


@pytest.mark.asyncio
async def test_ingest_log_invalid_information_data_key(http_client):
    app_token, _ = await _setup_app_token(http_client, suffix="5")

    r = await http_client.post(
        "/logs",
        headers={"Authorization": f"Bearer {app_token}"},
        json={
            "level": 2,
            "message": "Chave proibida",
            "environment": "test",
            "occurred_at": datetime.now(UTC).isoformat(),
            "information_data": {"$where": "1==1"},
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_logs(http_client):
    app_token, user_token = await _setup_app_token(http_client, suffix="6")

    # Ingere 3 logs
    for i in range(3):
        await http_client.post(
            "/logs",
            headers={"Authorization": f"Bearer {app_token}"},
            json={
                "level": 2,
                "message": f"Log {i}",
                "environment": "production",
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        )

    r = await http_client.get(
        "/logs",
        headers={"Authorization": f"Bearer {user_token}"},
        params={"limit": 2},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None
