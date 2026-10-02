import pytest


@pytest.mark.asyncio
async def test_health(http_client):
    response = await http_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mongodb"] == "up"
