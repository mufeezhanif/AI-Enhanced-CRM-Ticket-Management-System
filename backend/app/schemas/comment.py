from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.user import UserResponse


class CommentCreate(BaseModel):
    message: str
    is_internal: bool = False


class CommentResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    message: str
    is_internal: bool
    created_at: datetime
    agent: UserResponse | None = None

    model_config = {"from_attributes": True}
