from datetime import datetime
from uuid import UUID

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.errors import Forbidden, NotAuthenticated, PayloadTooLarge
from app.application.ports.application_repository import ApplicationRepository
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.log_repository import LogRepository
from app.application.use_cases.logs.ingest_log import IngestLog
from app.application.use_cases.logs.query_logs import QueryLogs
from app.interface.deps import (
    AppTokenClaims,
    UserTokenClaims,
    get_app_claims,
    get_app_repo,
    get_customer_repo,
    get_log_repo,
    get_user_claims,
)
from app.interface.schemas.log import (
    LogCreate,
    LogCreateResponse,
    LogListResponse,
    LogRead,
)

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("", response_model=LogCreateResponse, status_code=201)
async def ingest_log(
    body: LogCreate,
    claims: AppTokenClaims = Depends(get_app_claims),
    app_repo: ApplicationRepository = Depends(get_app_repo),
    customer_repo: CustomerRepository = Depends(get_customer_repo),
    log_repo: LogRepository = Depends(get_log_repo),
) -> LogCreateResponse:
    use_case = IngestLog(app_repo, customer_repo, log_repo)
    try:
        log_id = await use_case.execute(
            app_id_str=claims.app_id,
            correlation_id=body.correlation_id,
            level=int(body.level),
            message=body.message,
            exception=body.exception,
            environment=body.environment,
            information_data=body.information_data,
            tags=body.tags,
            occurred_at=body.occurred_at,
        )
    except NotAuthenticated:
        raise HTTPException(401, "Token inválido")
    except Forbidden:
        raise HTTPException(403, "Cliente inativo")
    except PayloadTooLarge:
        raise HTTPException(413, "information_data acima de 64 KB")
    return LogCreateResponse(id=str(log_id))


@router.get("", response_model=LogListResponse)  # noqa: E501
async def list_logs(
    application_id: str | None = Query(None, pattern=r"^[0-9a-f]{24}$"),
    min_level: int | None = Query(None, ge=0, le=5),
    correlation_id: UUID | None = Query(None),
    tags: list[str] = Query(default=[]),
    occurred_from: datetime | None = Query(None),
    occurred_to: datetime | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    claims: UserTokenClaims = Depends(get_user_claims),
    log_repo: LogRepository = Depends(get_log_repo),
) -> LogListResponse:
    customer_id = ObjectId(claims.customer_id)
    app_id = ObjectId(application_id) if application_id else None

    use_case = QueryLogs(log_repo)
    page = await use_case.execute(
        customer_id=customer_id,
        application_id=app_id,
        level_min=min_level,
        correlation_id=correlation_id,
        tags=tags,
        from_date=occurred_from,
        to_date=occurred_to,
        cursor=cursor,
        limit=limit,
    )
    return LogListResponse(
        items=[_to_response(log) for log in page.items],
        next_cursor=page.next_cursor,
    )


@router.get("/{log_id}", response_model=LogRead)
async def get_log(
    log_id: str,
    claims: UserTokenClaims = Depends(get_user_claims),
    log_repo: LogRepository = Depends(get_log_repo),
) -> LogRead:
    try:
        oid = ObjectId(log_id)
    except Exception:
        raise HTTPException(404, "Log não encontrado")

    customer_id = ObjectId(claims.customer_id)
    log = await log_repo.find_by_id(oid, customer_id)
    if log is None:
        raise HTTPException(404, "Log não encontrado")
    return _to_response(log)


def _to_response(log) -> LogRead:
    return LogRead(
        id=str(log.id),
        application_id=str(log.application_id),
        application_name=log.application_name,
        correlation_id=log.correlation_id,
        level=log.level,
        message=log.message,
        exception=log.exception,
        environment=log.environment,
        information_data=log.information_data,
        tags=log.tags,
        occurred_at=log.occurred_at,
        received_at=log.received_at,
        expire_at=log.expire_at,
    )
