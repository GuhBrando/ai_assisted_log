"""POST /customers — auto-cadastro de cliente com o primeiro usuário."""

from dataclasses import dataclass

from pwdlib import PasswordHash

from app.application.errors import Conflict
from app.application.models import CustomerDoc, UserDoc
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.user_repository import UserRepository
from app.domain.constraints import RETENTION_DAYS_MAX, RETENTION_DAYS_MIN

_pwd = PasswordHash.recommended()


@dataclass
class RegisterCustomerResult:
    customer: CustomerDoc
    user: UserDoc


class RegisterCustomer:
    def __init__(
        self,
        customer_repo: CustomerRepository,
        user_repo: UserRepository,
    ) -> None:
        self._customer_repo = customer_repo
        self._user_repo = user_repo

    async def execute(
        self,
        customer_name: str,
        retention_days: int,
        user_name: str,
        user_email: str,
        user_password: str,
    ) -> RegisterCustomerResult:
        if not (RETENTION_DAYS_MIN <= retention_days <= RETENTION_DAYS_MAX):
            from fastapi import HTTPException
            raise HTTPException(422, "retention_days fora dos limites permitidos")

        existing = await self._user_repo.find_by_email(user_email)
        if existing is not None:
            raise Conflict("E-mail já cadastrado")

        customer = await self._customer_repo.create(customer_name, retention_days)
        password_hash = _pwd.hash(user_password)
        user = await self._user_repo.create(customer.id, user_name, user_email, password_hash)
        return RegisterCustomerResult(customer=customer, user=user)
