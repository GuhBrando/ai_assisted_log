import os
from contextlib import asynccontextmanager

import pymongo
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.infrastructure.mongodb.client import create_mongo_client
from app.interface.routers import applications, auth, customers, logs, users

_STATUS_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    413: "Payload Too Large",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = create_mongo_client(os.environ["MONGODB_URI"])
    app.state.mongo_client = client
    yield
    await client.close()


app = FastAPI(title="API de Logs", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(logs.router)
app.include_router(customers.router)
app.include_router(users.router)
app.include_router(applications.router)


# --- Problem Details (RFC 9457, ADR-019) ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    content = {
        "type": f"https://httpstatuses.io/{exc.status_code}",
        "title": _STATUS_TITLES.get(exc.status_code, "Error"),
        "status": exc.status_code,
        "detail": exc.detail,
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=dict(exc.headers) if exc.headers else None,
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://httpstatuses.io/422",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": "Validação falhou",
            "errors": exc.errors(),
        },
        media_type="application/problem+json",
    )


@app.get("/health")
async def health(request: Request):
    try:
        # Sem limite, o ping esperaria o timeout padrão de 30 s para escolher um servidor.
        with pymongo.timeout(3):
            await request.app.state.mongo_client.admin.command("ping")
    except PyMongoError:
        return JSONResponse(status_code=503, content={"status": "unavailable", "mongodb": "down"})
    return {"status": "ok", "mongodb": "up"}
