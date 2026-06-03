from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.customer import Customer
from app.models.notification import NotificationLog
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket_query = db.query(Ticket)
    if current_user.role == UserRole.agent:
        ticket_query = ticket_query.filter(Ticket.assigned_agent_id == current_user.id)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_open = ticket_query.filter(
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
    ).count()

    resolved_today = ticket_query.filter(
        Ticket.resolved_at >= today_start
    ).count()

    critical_tickets = ticket_query.filter(Ticket.priority == TicketPriority.critical).count()

    if current_user.role == UserRole.manager:
        total_customers = db.query(Customer).count()
    else:
        total_customers = (
            db.query(Customer)
            .filter(Customer.assigned_agent_id == current_user.id)
            .count()
        )

    status_counts = {}
    for s in TicketStatus:
        status_counts[s.value] = ticket_query.filter(Ticket.status == s).count()

    priority_counts = {}
    for p in TicketPriority:
        priority_counts[p.value] = ticket_query.filter(Ticket.priority == p).count()

    return {
        "total_open": total_open,
        "resolved_today": resolved_today,
        "critical_tickets": critical_tickets,
        "total_customers": total_customers,
        "tickets_by_status": status_counts,
        "tickets_by_priority": priority_counts,
    }


@router.get("/agent-workloads")
def agent_workloads(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    week_ago = datetime.utcnow() - timedelta(days=7)
    agents = db.query(User).filter(User.role == UserRole.agent, User.is_active == True).all()
    result = []
    for agent in agents:
        tickets = db.query(Ticket).filter(Ticket.assigned_agent_id == agent.id)
        result.append(
            {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "total": tickets.count(),
                "open": tickets.filter(Ticket.status == TicketStatus.open).count(),
                "in_progress": tickets.filter(Ticket.status == TicketStatus.in_progress).count(),
                "resolved_this_week": tickets.filter(
                    Ticket.resolved_at >= week_ago
                ).count(),
            }
        )
    return result


@router.get("/notifications")
def recent_notifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    logs = (
        db.query(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": str(log.id),
            "ticket_id": str(log.ticket_id),
            "platform": log.platform,
            "status": log.status,
            "sent_at": log.sent_at,
            "message": log.message[:100],
        }
        for log in logs
    ]
