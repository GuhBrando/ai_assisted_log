"""POST /auth/login — login de usuário com e-mail e senha."""

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.application.errors import Forbidden, NotAuthenticated
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.user_repository import UserRepository

_pwd = PasswordHash.recommended()


@dataclass
class LoginResult:
    access_token: str
    token_type: str
    expires_in: int


class LoginUser:
    def __init__(
        self,
        user_repo: UserRepository,
        customer_repo: CustomerRepository,
    ) -> None:
        self._user_repo = user_repo
        self._customer_repo = customer_repo

    async def execute(self, email: str, password: str) -> LoginResult:
        user = await self._user_repo.find_by_email(email)
        if user is None or not _pwd.check(password, user.password_hash):
            raise NotAuthenticated

        customer = await self._customer_repo.find_by_id(user.customer_id)
        if customer is None or not customer.is_active:
            raise Forbidden

        now = datetime.now(UTC)
        exp = now + timedelta(hours=1)
        payload = {
            "sub": str(user.id),
            "aud": "user",
            "customer_id": str(user.customer_id),
            "iat": now,
            "exp": exp,
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")
        return LoginResult(access_token=token, token_type="bearer", expires_in=3600)
