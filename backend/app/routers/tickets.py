import asyncio
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user, require_manager
from app.models.comment import TicketComment
from app.models.notification import NotificationLog
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketListResponse, TicketResponse, TicketUpdate
from app.services.ai_service import analyze_sentiment, categorize_ticket, generate_ticket_summary
from app.services.messaging_service import send_ticket_notifications

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        ai_category=ticket.ai_category,
        ai_sentiment=ticket.ai_sentiment,
        ai_sentiment_score=ticket.ai_sentiment_score,
        ai_summary=ticket.ai_summary,
        customer_id=ticket.customer_id,
        assigned_agent_id=ticket.assigned_agent_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        customer=ticket.customer,
        assigned_agent=ticket.assigned_agent,
        comment_count=len(ticket.comments) if ticket.comments else 0,
    )


def _load_ticket(db: Session, ticket_id: UUID) -> Ticket | None:
    return (
        db.query(Ticket)
        .options(
            joinedload(Ticket.customer),
            joinedload(Ticket.assigned_agent),
            joinedload(Ticket.comments),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )


async def run_ai_analysis(ticket_id, title: str, description: str):
    db = SessionLocal()
    try:
        category_result, sentiment_result = await asyncio.gather(
            asyncio.to_thread(categorize_ticket, title, description),
            asyncio.to_thread(analyze_sentiment, description),
        )
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            ticket.ai_category = category_result.get("category")
            ticket.ai_sentiment = sentiment_result.get("sentiment")
            ticket.ai_sentiment_score = sentiment_result.get("score")
            if (
                sentiment_result.get("sentiment") == "frustrated"
                and ticket.status == TicketStatus.open
            ):
                ticket.priority = TicketPriority.critical
            db.commit()
    finally:
        db.close()


async def run_ai_summary(ticket_id):
    db = SessionLocal()
    try:
        ticket = (
            db.query(Ticket)
            .options(joinedload(Ticket.comments).joinedload(TicketComment.agent))
            .filter(Ticket.id == ticket_id)
            .first()
        )
        if not ticket:
            return
        comments_text = [
            f"{c.agent.name if c.agent else 'Agent'}: {c.message}" for c in ticket.comments
        ]
        summary = await asyncio.to_thread(
            generate_ticket_summary, ticket.title, ticket.description, comments_text
        )
        ticket.ai_summary = summary
        db.commit()
    finally:
        db.close()


async def run_notifications(ticket_id, event_type: str):
    db = SessionLocal()
    try:
        await send_ticket_notifications(ticket_id, event_type, db)
    finally:
        db.close()


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status_filter: TicketStatus | None = Query(None, alias="status"),
    priority: TicketPriority | None = None,
    category: str | None = None,
    agent_id: UUID | None = None,
    customer_id: UUID | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Ticket).options(
        joinedload(Ticket.customer),
        joinedload(Ticket.assigned_agent),
        joinedload(Ticket.comments),
    )

    if current_user.role == UserRole.agent:
        query = query.filter(Ticket.assigned_agent_id == current_user.id)
    elif agent_id:
        query = query.filter(Ticket.assigned_agent_id == agent_id)

    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if category:
        query = query.filter(
            or_(Ticket.category == category, Ticket.ai_category == category)
        )
    if customer_id:
        query = query.filter(Ticket.customer_id == customer_id)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Ticket.title).like(pattern),
                func.lower(Ticket.description).like(pattern),
            )
        )

    total = query.count()
    sort_col = getattr(Ticket, sort_by, Ticket.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    tickets = query.offset((page - 1) * size).limit(size).all()
    items = [_ticket_response(t) for t in tickets]
    return TicketListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()
    assigned = data.assigned_agent_id
    if not assigned and current_user.role == UserRole.agent:
        assigned = current_user.id

    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        category=data.category,
        customer_id=data.customer_id,
        assigned_agent_id=assigned,
        status=TicketStatus.open,
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    ticket = _load_ticket(db, ticket.id)

    if not os.environ.get("TESTING"):
        background_tasks.add_task(run_ai_analysis, ticket.id, ticket.title, ticket.description)
        background_tasks.add_task(run_notifications, ticket.id, "created")

    return _ticket_response(ticket)


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = _load_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.agent and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _ticket_response(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    data: TicketUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = _load_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.agent and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    old_status = ticket.status
    old_priority = ticket.priority
    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(ticket, field, value)

    ticket.updated_at = datetime.utcnow()

    if (
        ticket.ai_sentiment == "frustrated"
        and ticket.status == TicketStatus.open
        and "priority" not in updates
    ):
        ticket.priority = TicketPriority.critical

    if ticket.status == TicketStatus.resolved and old_status != TicketStatus.resolved:
        ticket.resolved_at = datetime.utcnow()
        if not os.environ.get("TESTING"):
            background_tasks.add_task(run_ai_summary, ticket.id)
            background_tasks.add_task(run_notifications, ticket.id, "resolved")

    if ticket.priority == TicketPriority.critical and old_priority != TicketPriority.critical:
        if not os.environ.get("TESTING"):
            background_tasks.add_task(run_notifications, ticket.id, "escalated")

    db.commit()
    db.refresh(ticket)
    ticket = _load_ticket(db, ticket_id)
    return _ticket_response(ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.delete(ticket)
    db.commit()


@router.post("/{ticket_id}/analyze", response_model=TicketResponse)
async def reanalyze_ticket(
    ticket_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = _load_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.agent and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.environ.get("TESTING"):
        background_tasks.add_task(run_ai_analysis, ticket.id, ticket.title, ticket.description)
    return _ticket_response(ticket)


@router.get("/{ticket_id}/notifications")
def get_ticket_notifications(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.ticket_id == ticket_id)
        .order_by(NotificationLog.sent_at.desc())
        .all()
    )
    return [
        {
            "id": str(log.id),
            "platform": log.platform,
            "status": log.status,
            "sent_at": log.sent_at,
            "message": log.message[:100],
        }
        for log in logs
    ]
