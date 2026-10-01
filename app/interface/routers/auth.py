from fastapi import APIRouter, Depends, Header, HTTPException

from app.application.errors import Forbidden, NotAuthenticated
from app.application.ports.application_repository import ApplicationRepository
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.user_repository import UserRepository
from app.application.use_cases.auth.issue_token import IssueToken
from app.application.use_cases.auth.login_user import LoginUser
from app.interface.deps import get_app_repo, get_customer_repo, get_user_repo
from app.interface.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    app_repo: ApplicationRepository = Depends(get_app_repo),
    customer_repo: CustomerRepository = Depends(get_customer_repo),
) -> TokenResponse:
    if x_api_key is None:
        raise HTTPException(401, "X-API-Key ausente")
    use_case = IssueToken(app_repo, customer_repo)
    try:
        result = await use_case.execute(x_api_key)
    except NotAuthenticated:
        raise HTTPException(401, "API key inválida, expirada ou revogada")
    except Forbidden:
        raise HTTPException(403, "Cliente inativo")
    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repo),
    customer_repo: CustomerRepository = Depends(get_customer_repo),
) -> TokenResponse:
    use_case = LoginUser(user_repo, customer_repo)
    try:
        result = await use_case.execute(body.email, body.password)
    except NotAuthenticated:
        raise HTTPException(401, "Credenciais inválidas")
    except Forbidden:
        raise HTTPException(403, "Cliente inativo")
    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )
