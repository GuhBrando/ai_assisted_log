from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.application.errors import Conflict, NotFound
from app.application.models import ApplicationDoc
from app.application.ports.application_repository import ApplicationRepository
from app.application.use_cases.applications.generate_api_key import GenerateApiKey
from app.application.use_cases.applications.register_application import RegisterApplication
from app.application.use_cases.applications.revoke_api_key import RevokeApiKey
from app.interface.deps import UserTokenClaims, get_app_repo, get_user_claims
from app.interface.schemas.application import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApplicationCreate,
    ApplicationResponse,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationResponse, status_code=201)
async def register_application(
    body: ApplicationCreate,
    claims: UserTokenClaims = Depends(get_user_claims),
    app_repo: ApplicationRepository = Depends(get_app_repo),
) -> ApplicationResponse:
    use_case = RegisterApplication(app_repo)
    try:
        app = await use_case.execute(
            customer_id=ObjectId(claims.customer_id),
            name=body.name,
            tags=body.tags,
        )
    except Conflict as e:
        raise HTTPException(409, str(e))
    return _to_response(app)


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    claims: UserTokenClaims = Depends(get_user_claims),
    app_repo: ApplicationRepository = Depends(get_app_repo),
) -> list[ApplicationResponse]:
    apps = await app_repo.list_by_customer(ObjectId(claims.customer_id))
    return [_to_response(a) for a in apps]


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: str,
    claims: UserTokenClaims = Depends(get_user_claims),
    app_repo: ApplicationRepository = Depends(get_app_repo),
) -> ApplicationResponse:
    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Aplicação não encontrada")
    app = await app_repo.find_by_id(oid)
    if app is None or app.customer_id != ObjectId(claims.customer_id):
        raise HTTPException(404, "Aplicação não encontrada")
    return _to_response(app)


@router.post("/{app_id}/api-keys", response_model=ApiKeyResponse, status_code=201)
async def generate_api_key(
    app_id: str,
    body: ApiKeyCreate,
    claims: UserTokenClaims = Depends(get_user_claims),
    app_repo: ApplicationRepository = Depends(get_app_repo),
) -> ApiKeyResponse:
    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Aplicação não encontrada")
    use_case = GenerateApiKey(app_repo)
    try:
        result = await use_case.execute(
            customer_id=ObjectId(claims.customer_id),
            app_id=oid,
            expires_at=body.expires_at,
        )
    except NotFound:
        raise HTTPException(404, "Aplicação não encontrada")
    return ApiKeyResponse(
        prefix=result.prefix,
        raw_key=result.raw_key,
        expires_at=result.expires_at,
    )


@router.post("/{app_id}/api-keys/{prefix}/revoke", status_code=204)
async def revoke_api_key(
    app_id: str,
    prefix: str,
    claims: UserTokenClaims = Depends(get_user_claims),
    app_repo: ApplicationRepository = Depends(get_app_repo),
) -> None:
    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Aplicação não encontrada")
    use_case = RevokeApiKey(app_repo)
    try:
        await use_case.execute(
            customer_id=ObjectId(claims.customer_id),
            app_id=oid,
            prefix=prefix,
        )
    except NotFound:
        raise HTTPException(404, "Aplicação ou chave não encontrada")


def _to_response(a: ApplicationDoc) -> ApplicationResponse:
    return ApplicationResponse(
        id=str(a.id),
        customer_id=str(a.customer_id),
        name=a.name,
        tags=a.tags,
        created_at=a.created_at,
    )
