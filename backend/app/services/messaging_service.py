import asyncio
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import uuid4

import requests
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.notification import NotificationLog
from app.models.ticket import Ticket


def _credentials_configured() -> bool:
    gmail_ok = bool(
        settings.GMAIL_USER
        and settings.GMAIL_APP_PASSWORD
        and not settings.GMAIL_USER.startswith("your-")
    )
    telegram_ok = bool(
        settings.TELEGRAM_BOT_TOKEN
        and settings.TELEGRAM_CHAT_ID
        and not settings.TELEGRAM_BOT_TOKEN.startswith("your-")
    )
    return gmail_ok or telegram_ok


def send_email(to_email: str, subject: str, body_html: str) -> bool:
    if not settings.GMAIL_USER or settings.GMAIL_USER.startswith("your-"):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.GMAIL_USER
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def send_telegram_message(message: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN.startswith("your-"):
        return False
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def log_notification(
    db: Session,
    ticket_id,
    platform: str,
    message: str,
    status: str,
    error=None,
):
    log = NotificationLog(
        id=uuid4(),
        ticket_id=ticket_id,
        platform=platform,
        message=message[:500],
        status=status,
        sent_at=datetime.utcnow(),
        error_message=str(error)[:200] if error else None,
    )
    db.add(log)
    db.commit()


def _ticket_short_id(ticket_id) -> str:
    return str(ticket_id)[:8]


def notify_ticket_created_email(ticket, customer, agent_email: str) -> bool:
    desc = (ticket.description or "")[:200]
    body = f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2>New Support Ticket</h2>
    <p><strong>#{_ticket_short_id(ticket.id)}</strong> — {ticket.title}</p>
    <p><strong>Customer:</strong> {customer.full_name}</p>
    <p><strong>Priority:</strong> {ticket.priority.value.upper()}</p>
    <p><strong>Description:</strong> {desc}</p>
    </body></html>
    """
    return send_email(agent_email, f"[New Ticket #{_ticket_short_id(ticket.id)}] {ticket.title}", body)


def notify_ticket_created_telegram(ticket, customer) -> bool:
    agent_name = ticket.assigned_agent.name if ticket.assigned_agent else "Unassigned"
    msg = (
        f"🎫 <b>New Ticket Created</b>\n"
        f"ID: #{_ticket_short_id(ticket.id)}\n"
        f"Title: {ticket.title}\n"
        f"Customer: {customer.full_name}\n"
        f"Priority: {ticket.priority.value.upper()}\n"
        f"Agent: {agent_name}"
    )
    return send_telegram_message(msg)


def notify_ticket_resolved_email(ticket, customer) -> bool:
    summary = ticket.ai_summary or "Your issue has been addressed by our support team."
    body = f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2>Ticket Resolved</h2>
    <p>Hi {customer.full_name},</p>
    <p>Your support ticket <strong>{ticket.title}</strong> has been resolved.</p>
    <p><strong>Summary:</strong> {summary}</p>
    <p>Thank you for contacting us.</p>
    </body></html>
    """
    return send_email(
        customer.email,
        f"Your support ticket has been resolved — {ticket.title}",
        body,
    )


def notify_ticket_resolved_telegram(ticket, customer) -> bool:
    msg = (
        f"✅ <b>Ticket Resolved</b>\n"
        f"ID: #{_ticket_short_id(ticket.id)}\n"
        f"Title: {ticket.title}\n"
        f"Customer: {customer.full_name}"
    )
    return send_telegram_message(msg)


def notify_ticket_escalated_email(ticket, customer, agent_email: str) -> bool:
    body = f"""
    <html><body style="font-family:Arial,sans-serif;">
    <div style="background:#dc2626;color:white;padding:12px;font-weight:bold;">
    🚨 CRITICAL ESCALATION
    </div>
    <p><strong>Ticket:</strong> {ticket.title}</p>
    <p><strong>Customer:</strong> {customer.full_name}</p>
    <p><strong>Reason:</strong> Priority changed to CRITICAL</p>
    </body></html>
    """
    return send_email(agent_email, f"🚨 [CRITICAL] Ticket Escalated: {ticket.title}", body)


def notify_ticket_escalated_telegram(ticket, customer) -> bool:
    msg = (
        f"🚨 <b>CRITICAL ESCALATION</b>\n"
        f"Ticket: {ticket.title}\n"
        f"Customer: {customer.full_name}\n"
        f"Reason: Priority changed to CRITICAL"
    )
    return send_telegram_message(msg)


async def send_ticket_notifications(ticket_id, event_type: str, db: Session):
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.customer),
            joinedload(Ticket.assigned_agent),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        return

    customer = ticket.customer
    agent_email = (
        ticket.assigned_agent.email if ticket.assigned_agent else settings.GMAIL_USER
    )

    gmail_configured = bool(
        settings.GMAIL_USER and not settings.GMAIL_USER.startswith("your-")
    )
    telegram_configured = bool(
        settings.TELEGRAM_BOT_TOKEN and not settings.TELEGRAM_BOT_TOKEN.startswith("your-")
    )

    if event_type == "created":
        if not gmail_configured and not telegram_configured:
            log_notification(
                db, ticket.id, "email", "Messaging credentials not configured — notification skipped", "skipped"
            )
            return

        if gmail_configured:
            success = await asyncio.to_thread(
                notify_ticket_created_email, ticket, customer, agent_email
            )
            log_notification(
                db, ticket.id, "email", "New ticket notification", "sent" if success else "failed"
            )
        else:
            log_notification(db, ticket.id, "email", "Gmail not configured", "skipped")

        if telegram_configured:
            success = await asyncio.to_thread(notify_ticket_created_telegram, ticket, customer)
            log_notification(
                db, ticket.id, "telegram", "New ticket notification", "sent" if success else "failed"
            )
        else:
            log_notification(db, ticket.id, "telegram", "Telegram not configured", "skipped")

    elif event_type == "resolved":
        if gmail_configured:
            success = await asyncio.to_thread(notify_ticket_resolved_email, ticket, customer)
            log_notification(
                db, ticket.id, "email", "Resolution notification", "sent" if success else "failed"
            )
        if telegram_configured:
            success = await asyncio.to_thread(notify_ticket_resolved_telegram, ticket, customer)
            log_notification(
                db, ticket.id, "telegram", "Resolution notification", "sent" if success else "failed"
            )

    elif event_type == "escalated":
        if gmail_configured:
            success = await asyncio.to_thread(
                notify_ticket_escalated_email, ticket, customer, agent_email
            )
            log_notification(
                db, ticket.id, "email", "Escalation notification", "sent" if success else "failed"
            )
        if telegram_configured:
            success = await asyncio.to_thread(notify_ticket_escalated_telegram, ticket, customer)
            log_notification(
                db, ticket.id, "telegram", "Escalation notification", "sent" if success else "failed"
            )
