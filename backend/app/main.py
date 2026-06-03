import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.dependencies import get_password_hash
from app.models import NotificationLog, TicketComment, Customer, Ticket, User
from app.models.user import UserRole
from app.routers import auth, comments, customers, dashboard, tickets, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI CRM System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.on_event("startup")
def startup():
    import os
    if os.environ.get("TESTING"):
        return
    Base.metadata.create_all(bind=engine)
    seed_default_users()


def seed_default_users():
    db = SessionLocal()
    try:
        manager = db.query(User).filter(User.role == UserRole.manager).first()
        if not manager:
            db.add(
                User(
                    name="Admin Manager",
                    email="admin@crm.com",
                    password_hash=get_password_hash("admin123"),
                    role=UserRole.manager,
                )
            )
            db.add(
                User(
                    name="Agent Sarah",
                    email="sarah@crm.com",
                    password_hash=get_password_hash("agent123"),
                    role=UserRole.agent,
                )
            )
            db.commit()
            logger.info("Default users created: admin@crm.com / sarah@crm.com")
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "AI CRM API running", "version": "1.0.0"}
