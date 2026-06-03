from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.customer import CustomerResponse
from app.schemas.user import UserResponse


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: TicketPriority = TicketPriority.medium
    customer_id: UUID
    assigned_agent_id: UUID | None = None
    category: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: str | None = None
    assigned_agent_id: UUID | None = None


class TicketResponse(BaseModel):
    id: UUID
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str | None
    ai_category: str | None
    ai_sentiment: str | None
    ai_sentiment_score: float | None
    ai_summary: str | None
    customer_id: UUID
    assigned_agent_id: UUID | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    customer: CustomerResponse | None = None
    assigned_agent: UserResponse | None = None
    comment_count: int = 0

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    size: int
