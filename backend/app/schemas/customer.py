from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class CustomerCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    notes: str | None = None
    assigned_agent_id: UUID | None = None


class CustomerUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    notes: str | None = None
    assigned_agent_id: UUID | None = None


class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    phone: str | None
    company: str | None
    notes: str | None
    created_at: datetime
    assigned_agent_id: UUID | None
    assigned_agent: UserResponse | None = None
    ticket_count: int | None = None
    last_ticket_date: datetime | None = None
    open_tickets: int | None = None

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    size: int
