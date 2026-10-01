"""Dependências FastAPI: acesso ao DB, repositórios e autenticação JWT."""

import os
from dataclasses import dataclass
from datetime import datetime

import jwt
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.ports.application_repository import ApplicationRepository
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.log_repository import LogRepository
from app.application.ports.user_repository import UserRepository
from app.infrastructure.mongodb.client import MongoDatabase
from app.infrastructure.mongodb.repositories.application_repository import (
    MongoApplicationRepository,
)
from app.infrastructure.mongodb.repositories.customer_repository import MongoCustomerRepository
from app.infrastructure.mongodb.repositories.log_repository import MongoLogRepository
from app.infrastructure.mongodb.repositories.user_repository import MongoUserRepository

_bearer = HTTPBearer(auto_error=False)


def get_db(request: Request) -> MongoDatabase:
    return request.app.state.mongo_client.get_default_database()


def get_customer_repo(db: MongoDatabase = Depends(get_db)) -> CustomerRepository:
    return MongoCustomerRepository(db)


def get_user_repo(db: MongoDatabase = Depends(get_db)) -> UserRepository:
    return MongoUserRepository(db)


def get_app_repo(db: MongoDatabase = Depends(get_db)) -> ApplicationRepository:
    return MongoApplicationRepository(db)


def get_log_repo(db: MongoDatabase = Depends(get_db)) -> LogRepository:
    return MongoLogRepository(db)


# --- JWT de aplicação (POST /logs) ---

@dataclass
class AppTokenClaims:
    app_id: str
    exp: datetime
    jti: str


async def get_app_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AppTokenClaims:
    if credentials is None:
        raise HTTPException(401, "Token ausente")
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.environ["JWT_SECRET"],
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "jti"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido")

    # Rejeita tokens de usuário usados em rotas de aplicação
    if payload.get("aud") == "user":
        raise HTTPException(401, "Token inválido para esta rota")

    return AppTokenClaims(
        app_id=payload["sub"],
        exp=payload["exp"],
        jti=payload["jti"],
    )


# --- JWT de usuário (rotas do painel) ---

@dataclass
class UserTokenClaims:
    user_id: str
    customer_id: str


async def get_user_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserTokenClaims:
    if credentials is None:
        raise HTTPException(401, "Token ausente")
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.environ["JWT_SECRET"],
            algorithms=["HS256"],
            audience="user",
            options={"require": ["sub", "exp", "jti", "customer_id"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido")

    return UserTokenClaims(
        user_id=payload["sub"],
        customer_id=payload["customer_id"],
    )
