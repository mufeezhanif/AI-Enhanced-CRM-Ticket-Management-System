from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.customer import Customer
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.ticket import TicketResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/customers", tags=["customers"])


def _customer_response(customer: Customer, db: Session) -> CustomerResponse:
    ticket_count = db.query(Ticket).filter(Ticket.customer_id == customer.id).count()
    open_tickets = (
        db.query(Ticket)
        .filter(
            Ticket.customer_id == customer.id,
            Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]),
        )
        .count()
    )
    last_ticket = (
        db.query(func.max(Ticket.created_at))
        .filter(Ticket.customer_id == customer.id)
        .scalar()
    )
    resp = CustomerResponse.model_validate(customer)
    resp.ticket_count = ticket_count
    resp.open_tickets = open_tickets
    resp.last_ticket_date = last_ticket
    if customer.assigned_agent:
        resp.assigned_agent = UserResponse.model_validate(customer.assigned_agent)
    return resp


@router.get("", response_model=CustomerListResponse)
def list_customers(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    agent_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Customer).options(joinedload(Customer.assigned_agent))

    if current_user.role == UserRole.agent:
        query = query.filter(Customer.assigned_agent_id == current_user.id)
    elif agent_id:
        query = query.filter(Customer.assigned_agent_id == agent_id)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Customer.full_name).like(pattern),
                func.lower(Customer.email).like(pattern),
                func.lower(Customer.company).like(pattern),
            )
        )

    total = query.count()
    customers = (
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    items = [_customer_response(c, db) for c in customers]
    return CustomerListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = data.model_dump()
    if current_user.role == UserRole.agent:
        payload["assigned_agent_id"] = current_user.id
    customer = Customer(**payload)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    customer = (
        db.query(Customer)
        .options(joinedload(Customer.assigned_agent))
        .filter(Customer.id == customer.id)
        .first()
    )
    return _customer_response(customer, db)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = (
        db.query(Customer)
        .options(joinedload(Customer.assigned_agent))
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if current_user.role == UserRole.agent and customer.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _customer_response(customer, db)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = (
        db.query(Customer)
        .options(joinedload(Customer.assigned_agent))
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if current_user.role == UserRole.agent and customer.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return _customer_response(customer, db)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()


@router.get("/{customer_id}/tickets", response_model=list[TicketResponse])
def get_customer_tickets(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if current_user.role == UserRole.agent and customer.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Ticket).filter(Ticket.customer_id == customer_id)
    if current_user.role == UserRole.agent:
        query = query.filter(Ticket.assigned_agent_id == current_user.id)
    from app.routers.tickets import _ticket_response

    tickets = query.options(
        joinedload(Ticket.customer),
        joinedload(Ticket.assigned_agent),
        joinedload(Ticket.comments),
    ).order_by(Ticket.created_at.desc()).all()
    return [_ticket_response(t) for t in tickets]
