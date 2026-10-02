"""Testes de autenticação: POST /customers → POST /applications → POST /applications/{id}/api-keys → POST /auth/token."""

import pytest


@pytest.mark.asyncio
async def test_full_auth_flow(http_client):
    # 1. Cadastra cliente + usuário
    r = await http_client.post("/customers", json={
        "name": "Acme Corp",
        "retention_days": 30,
        "user_name": "João",
        "user_email": "joao@acme.com",
        "user_password": "senha12345",
    })
    assert r.status_code == 201, r.text
    assert r.json()["is_active"] is True

    # 2. Login do usuário
    r = await http_client.post("/auth/login", json={
        "email": "joao@acme.com",
        "password": "senha12345",
    })
    assert r.status_code == 200, r.text
    user_token = r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"

    # 3. Cadastra aplicação
    r = await http_client.post(
        "/applications",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"name": "Checkout Service", "tags": ["team:payments"]},
    )
    assert r.status_code == 201, r.text
    app_id = r.json()["id"]
    assert r.json()["tags"] == ["team:payments"]

    # 4. Gera API key
    r = await http_client.post(
        f"/applications/{app_id}/api-keys",
        headers={"Authorization": f"Bearer {user_token}"},
        json={},
    )
    assert r.status_code == 201, r.text
    raw_key = r.json()["raw_key"]
    prefix = r.json()["prefix"]
    assert raw_key.startswith("lx_")

    # 5. Troca API key por token de aplicação
    r = await http_client.post("/auth/token", headers={"X-API-Key": raw_key})
    assert r.status_code == 200, r.text
    app_token = r.json()["access_token"]
    assert r.json()["expires_in"] <= 3600

    return app_token, user_token, app_id, raw_key, prefix


@pytest.mark.asyncio
async def test_token_missing_api_key(http_client):
    r = await http_client.post("/auth/token")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_token_invalid_api_key(http_client):
    r = await http_client.post("/auth/token", headers={"X-API-Key": "lx_invalida"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_password(http_client):
    # Cria usuário primeiro
    await http_client.post("/customers", json={
        "name": "Corp B",
        "retention_days": 7,
        "user_name": "Maria",
        "user_email": "maria@corp.com",
        "user_password": "senhavalida123",
    })
    r = await http_client.post("/auth/login", json={
        "email": "maria@corp.com",
        "password": "senhaerrada",
    })
    assert r.status_code == 401
