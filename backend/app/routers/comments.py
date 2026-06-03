from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.comment import TicketComment
from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.user import UserResponse

router = APIRouter(tags=["comments"])


@router.get("/tickets/{ticket_id}/comments", response_model=list[CommentResponse])
def list_comments(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.agent and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    comments = (
        db.query(TicketComment)
        .options(joinedload(TicketComment.agent))
        .filter(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
        .all()
    )

    result = []
    for c in comments:
        if c.is_internal and current_user.role == UserRole.agent and c.agent_id != current_user.id:
            continue
        result.append(
            CommentResponse(
                id=c.id,
                ticket_id=c.ticket_id,
                message=c.message,
                is_internal=c.is_internal,
                created_at=c.created_at,
                agent=UserResponse.model_validate(c.agent) if c.agent else None,
            )
        )
    return result


@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    ticket_id: UUID,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.agent and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    comment = TicketComment(
        ticket_id=ticket_id,
        agent_id=current_user.id,
        message=data.message,
        is_internal=data.is_internal,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment = (
        db.query(TicketComment)
        .options(joinedload(TicketComment.agent))
        .filter(TicketComment.id == comment.id)
        .first()
    )
    return CommentResponse(
        id=comment.id,
        ticket_id=comment.ticket_id,
        message=comment.message,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
        agent=UserResponse.model_validate(comment.agent),
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(TicketComment).filter(TicketComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.agent_id != current_user.id and current_user.role != UserRole.manager:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(comment)
    db.commit()
