import os
from contextlib import asynccontextmanager

import pymongo
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(
        os.environ["MONGODB_URI"],
        uuidRepresentation="standard",
        tz_aware=True,
    )
    app.state.mongo_client = client
    yield
    await client.close()


app = FastAPI(title="API de Logs", lifespan=lifespan)


@app.get("/health")
async def health(request: Request):
    try:
        # Sem limite, o ping esperaria o timeout padrão de 30 s para escolher um servidor.
        with pymongo.timeout(3):
            await request.app.state.mongo_client.admin.command("ping")
    except PyMongoError:
        return JSONResponse(status_code=503, content={"status": "unavailable", "mongodb": "down"})
    return {"status": "ok", "mongodb": "up"}
