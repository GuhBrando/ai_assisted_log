from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.application.errors import Conflict
from app.application.models import UserDoc
from app.application.ports.user_repository import UserRepository
from app.application.use_cases.users.register_user import RegisterUser
from app.interface.deps import UserTokenClaims, get_user_claims, get_user_repo
from app.interface.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
async def register_user(
    body: UserCreate,
    claims: UserTokenClaims = Depends(get_user_claims),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserResponse:
    use_case = RegisterUser(user_repo)
    try:
        user = await use_case.execute(
            customer_id=ObjectId(claims.customer_id),
            name=body.name,
            email=body.email,
            password=body.password,
        )
    except Conflict as e:
        raise HTTPException(409, str(e))
    return _to_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    claims: UserTokenClaims = Depends(get_user_claims),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserResponse:
    user = await user_repo.find_by_id(ObjectId(claims.user_id))
    if user is None:
        raise HTTPException(404, "Usuário não encontrado")
    return _to_response(user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    claims: UserTokenClaims = Depends(get_user_claims),
    user_repo: UserRepository = Depends(get_user_repo),
) -> list[UserResponse]:
    users = await user_repo.list_by_customer(ObjectId(claims.customer_id))
    return [_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    claims: UserTokenClaims = Depends(get_user_claims),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserResponse:
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Usuário não encontrado")
    user = await user_repo.find_by_id(oid)
    if user is None or user.customer_id != ObjectId(claims.customer_id):
        raise HTTPException(404, "Usuário não encontrado")
    return _to_response(user)


def _to_response(u: UserDoc) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        customer_id=str(u.customer_id),
        name=u.name,
        email=u.email,
        created_at=u.created_at,
    )
