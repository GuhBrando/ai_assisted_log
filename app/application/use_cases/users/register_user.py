"""POST /users — cadastro de usuário adicional dentro de um cliente."""

from bson import ObjectId
from pwdlib import PasswordHash

from app.application.errors import Conflict
from app.application.models import UserDoc
from app.application.ports.user_repository import UserRepository

_pwd = PasswordHash.recommended()


class RegisterUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(
        self,
        customer_id: ObjectId,
        name: str,
        email: str,
        password: str,
    ) -> UserDoc:
        existing = await self._user_repo.find_by_email(email)
        if existing is not None:
            raise Conflict("E-mail já cadastrado")

        password_hash = _pwd.hash(password)
        return await self._user_repo.create(customer_id, name, email, password_hash)
