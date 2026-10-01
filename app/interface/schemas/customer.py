from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.constraints import RETENTION_DAYS_MAX, RETENTION_DAYS_MIN


class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    retention_days: int = Field(default=90, ge=RETENTION_DAYS_MIN, le=RETENTION_DAYS_MAX)
    user_name: str = Field(min_length=1)
    user_email: EmailStr
    user_password: str = Field(min_length=8, max_length=128)


class CustomerResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    retention_days: int
    created_at: datetime
