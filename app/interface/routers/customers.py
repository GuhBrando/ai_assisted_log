from fastapi import APIRouter, Depends, HTTPException

from app.application.errors import Conflict
from app.application.models import CustomerDoc, UserDoc
from app.application.ports.customer_repository import CustomerRepository
from app.application.ports.user_repository import UserRepository
from app.application.use_cases.customers.register_customer import RegisterCustomer
from app.interface.deps import UserTokenClaims, get_customer_repo, get_user_claims, get_user_repo
from app.interface.schemas.customer import CustomerCreate, CustomerResponse
from bson import ObjectId

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def register_customer(
    body: CustomerCreate,
    customer_repo: CustomerRepository = Depends(get_customer_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> CustomerResponse:
    use_case = RegisterCustomer(customer_repo, user_repo)
    try:
        result = await use_case.execute(
            customer_name=body.name,
            retention_days=body.retention_days,
            user_name=body.user_name,
            user_email=body.user_email,
            user_password=body.user_password,
        )
    except Conflict as e:
        raise HTTPException(409, str(e))
    return _customer_to_response(result.customer)


@router.get("/me", response_model=CustomerResponse)
async def get_my_customer(
    claims: UserTokenClaims = Depends(get_user_claims),
    customer_repo: CustomerRepository = Depends(get_customer_repo),
) -> CustomerResponse:
    customer = await customer_repo.get_me(ObjectId(claims.customer_id))
    if customer is None:
        raise HTTPException(404, "Cliente não encontrado")
    return _customer_to_response(customer)


def _customer_to_response(c: CustomerDoc) -> CustomerResponse:
    return CustomerResponse(
        id=str(c.id),
        name=c.name,
        is_active=c.is_active,
        retention_days=c.retention_days,
        created_at=c.created_at,
    )
