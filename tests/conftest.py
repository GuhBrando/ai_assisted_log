"""Fixtures compartilhadas: container MongoDB + cliente HTTP da FastAPI."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from testcontainers.mongodb import MongoDbContainer

from app.infrastructure.mongodb.client import create_mongo_client
from app.infrastructure.mongodb.migrate import apply_schema
from app.main import app


@pytest.fixture(scope="session")
def mongo_container():
    with MongoDbContainer("mongo:8.0") as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def mongo_uri(mongo_container):
    # O usuário root do container fica no banco admin; sem authSource, a autenticação falha.
    uri = mongo_container.get_connection_url() + "/log_api_test?authSource=admin"
    os.environ["MONGODB_URI"] = uri
    os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long!")

    client = create_mongo_client(uri)
    await apply_schema(client.get_default_database())
    yield uri
    await client.close()


@pytest_asyncio.fixture
async def http_client(mongo_uri):
    # O ASGITransport não executa o lifespan; sem ele, app.state.mongo_client não existe.
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
