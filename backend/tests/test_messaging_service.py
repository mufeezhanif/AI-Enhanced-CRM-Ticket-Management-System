"""
Messaging service tests: email, Telegram, notification logging, and send_ticket_notifications.
All network calls are mocked — no real emails or Telegram messages sent.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.messaging_service import (
    log_notification,
    send_email,
    send_telegram_message,
    send_ticket_notifications,
)


# ─── send_email ──────────────────────────────────────────────────────────────

class TestSendEmail:
    def test_skips_when_gmail_not_configured(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = ""
            mock_settings.GMAIL_APP_PASSWORD = ""
            result = send_email("to@test.com", "Subject", "<p>Body</p>")
        assert result is False

    def test_skips_when_gmail_placeholder(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = "your-gmail@gmail.com"
            mock_settings.GMAIL_APP_PASSWORD = "your-app-password"
            result = send_email("to@test.com", "Subject", "<p>Body</p>")
        assert result is False

    def test_returns_true_on_success(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = "real@gmail.com"
            mock_settings.GMAIL_APP_PASSWORD = "realapppassword"
            with patch("smtplib.SMTP_SSL") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                result = send_email("to@test.com", "Test Subject", "<p>Hello</p>")
        assert result is True
        mock_server.login.assert_called_once_with("real@gmail.com", "realapppassword")
        mock_server.sendmail.assert_called_once()

    def test_returns_false_on_smtp_error(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = "real@gmail.com"
            mock_settings.GMAIL_APP_PASSWORD = "realapppassword"
            with patch("smtplib.SMTP_SSL", side_effect=Exception("Connection refused")):
                result = send_email("to@test.com", "Subject", "<p>Body</p>")
        assert result is False


# ─── send_telegram_message ───────────────────────────────────────────────────

class TestSendTelegramMessage:
    def test_skips_when_token_not_configured(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = ""
            mock_settings.TELEGRAM_CHAT_ID = ""
            result = send_telegram_message("test message")
        assert result is False

    def test_skips_when_token_placeholder(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "your-telegram-bot-token"
            mock_settings.TELEGRAM_CHAT_ID = "-123"
            result = send_telegram_message("test message")
        assert result is False

    def test_returns_true_on_200_response(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "1234:ABCdef"
            mock_settings.TELEGRAM_CHAT_ID = "-1001234"
            with patch("requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                result = send_telegram_message("Hello from CRM")
        assert result is True
        call_args = mock_post.call_args
        assert "sendMessage" in call_args[0][0]
        assert call_args[1]["json"]["text"] == "Hello from CRM"
        assert call_args[1]["json"]["chat_id"] == "-1001234"

    def test_returns_false_on_non_200_response(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "1234:ABCdef"
            mock_settings.TELEGRAM_CHAT_ID = "-1001234"
            with patch("requests.post") as mock_post:
                mock_post.return_value.status_code = 400
                result = send_telegram_message("Test")
        assert result is False

    def test_returns_false_on_network_error(self):
        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "1234:ABCdef"
            mock_settings.TELEGRAM_CHAT_ID = "-1001234"
            with patch("requests.post", side_effect=Exception("Network timeout")):
                result = send_telegram_message("Test")
        assert result is False


# ─── log_notification ─────────────────────────────────────────────────────────

class TestLogNotification:
    def test_creates_log_entry(self, test_db):
        from app.models.notification import NotificationLog
        from app.models.customer import Customer
        from app.models.ticket import Ticket
        from app.models.user import User, UserRole
        from app.dependencies import get_password_hash

        user = User(
            name="Logger",
            email="logger@test.com",
            password_hash=get_password_hash("pass"),
            role=UserRole.manager,
        )
        test_db.add(user)
        test_db.flush()

        customer = Customer(full_name="Log Cust", email="logcust@test.com", created_at=datetime.utcnow())
        test_db.add(customer)
        test_db.flush()

        ticket = Ticket(
            title="Log ticket",
            description="desc",
            customer_id=customer.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_db.add(ticket)
        test_db.commit()

        log_notification(test_db, ticket.id, "email", "Test notification message", "sent")

        log = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).first()
        assert log is not None
        assert log.platform == "email"
        assert log.status == "sent"
        assert log.message == "Test notification message"
        assert log.error_message is None

    def test_logs_failed_status_with_error(self, test_db):
        from app.models.notification import NotificationLog
        from app.models.customer import Customer
        from app.models.ticket import Ticket
        from app.models.user import User, UserRole
        from app.dependencies import get_password_hash

        user = User(
            name="ErrLogger",
            email="errlogger@test.com",
            password_hash=get_password_hash("pass"),
            role=UserRole.manager,
        )
        test_db.add(user)
        test_db.flush()

        customer = Customer(full_name="Err Cust", email="errcust@test.com", created_at=datetime.utcnow())
        test_db.add(customer)
        test_db.flush()

        ticket = Ticket(
            title="Error log ticket",
            description="desc",
            customer_id=customer.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_db.add(ticket)
        test_db.commit()

        log_notification(test_db, ticket.id, "telegram", "Failed msg", "failed", error="Connection refused")

        log = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).first()
        assert log.status == "failed"
        assert "Connection refused" in log.error_message


# ─── send_ticket_notifications (async) ───────────────────────────────────────

class TestSendTicketNotifications:
    """Tests for the orchestrator that sends email+telegram per event type."""

    def _make_ticket(self, test_db, event="created"):
        from app.models.customer import Customer
        from app.models.ticket import Ticket
        from app.models.user import User, UserRole
        from app.dependencies import get_password_hash

        agent = User(
            name="Notif Agent",
            email=f"notifagent_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=get_password_hash("pass"),
            role=UserRole.agent,
        )
        test_db.add(agent)
        test_db.flush()

        customer = Customer(
            full_name="Notif Customer",
            email=f"notifcust_{uuid.uuid4().hex[:6]}@test.com",
            created_at=datetime.utcnow(),
            assigned_agent_id=agent.id,
        )
        test_db.add(customer)
        test_db.flush()

        ticket = Ticket(
            title="Notification test ticket",
            description="desc",
            customer_id=customer.id,
            assigned_agent_id=agent.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_db.add(ticket)
        test_db.commit()
        return ticket

    @pytest.mark.asyncio
    async def test_skipped_notification_when_no_credentials(self, test_db):
        from app.models.notification import NotificationLog

        ticket = self._make_ticket(test_db)

        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = ""
            mock_settings.GMAIL_APP_PASSWORD = ""
            mock_settings.TELEGRAM_BOT_TOKEN = ""
            mock_settings.TELEGRAM_CHAT_ID = ""
            await send_ticket_notifications(ticket.id, "created", test_db)

        log = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).first()
        assert log is not None
        assert log.status == "skipped"

    @pytest.mark.asyncio
    async def test_email_sent_on_ticket_created(self, test_db):
        from app.models.notification import NotificationLog

        ticket = self._make_ticket(test_db)

        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = "real@gmail.com"
            mock_settings.GMAIL_APP_PASSWORD = "apppass"
            mock_settings.TELEGRAM_BOT_TOKEN = ""
            mock_settings.TELEGRAM_CHAT_ID = ""
            with patch("app.services.messaging_service.notify_ticket_created_email", return_value=True) as mock_email:
                with patch("app.services.messaging_service.notify_ticket_created_telegram", return_value=False):
                    await send_ticket_notifications(ticket.id, "created", test_db)

        logs = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).all()
        email_logs = [l for l in logs if l.platform == "email"]
        assert any(l.status == "sent" for l in email_logs)

    @pytest.mark.asyncio
    async def test_telegram_sent_on_ticket_resolved(self, test_db):
        from app.models.notification import NotificationLog

        ticket = self._make_ticket(test_db)

        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = ""
            mock_settings.GMAIL_APP_PASSWORD = ""
            mock_settings.TELEGRAM_BOT_TOKEN = "1234:real"
            mock_settings.TELEGRAM_CHAT_ID = "-100123"
            with patch("app.services.messaging_service.notify_ticket_resolved_telegram", return_value=True):
                with patch("app.services.messaging_service.notify_ticket_resolved_email", return_value=False):
                    await send_ticket_notifications(ticket.id, "resolved", test_db)

        logs = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).all()
        telegram_logs = [l for l in logs if l.platform == "telegram"]
        assert any(l.status == "sent" for l in telegram_logs)

    @pytest.mark.asyncio
    async def test_escalation_notifications_sent(self, test_db):
        from app.models.notification import NotificationLog

        ticket = self._make_ticket(test_db)

        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = "real@gmail.com"
            mock_settings.GMAIL_APP_PASSWORD = "apppass"
            mock_settings.TELEGRAM_BOT_TOKEN = "1234:real"
            mock_settings.TELEGRAM_CHAT_ID = "-100123"
            with patch("app.services.messaging_service.notify_ticket_escalated_email", return_value=True):
                with patch("app.services.messaging_service.notify_ticket_escalated_telegram", return_value=True):
                    await send_ticket_notifications(ticket.id, "escalated", test_db)

        logs = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).all()
        assert len(logs) == 2
        assert all(l.status == "sent" for l in logs)

    @pytest.mark.asyncio
    async def test_notification_logged_as_failed_on_send_error(self, test_db):
        from app.models.notification import NotificationLog

        ticket = self._make_ticket(test_db)

        with patch("app.services.messaging_service.settings") as mock_settings:
            mock_settings.GMAIL_USER = "real@gmail.com"
            mock_settings.GMAIL_APP_PASSWORD = "apppass"
            mock_settings.TELEGRAM_BOT_TOKEN = ""
            mock_settings.TELEGRAM_CHAT_ID = ""
            with patch("app.services.messaging_service.notify_ticket_created_email", return_value=False):
                with patch("app.services.messaging_service.notify_ticket_created_telegram", return_value=False):
                    await send_ticket_notifications(ticket.id, "created", test_db)

        logs = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == ticket.id).all()
        email_logs = [l for l in logs if l.platform == "email"]
        assert any(l.status == "failed" for l in email_logs)

    @pytest.mark.asyncio
    async def test_no_notification_for_missing_ticket(self, test_db):
        from app.models.notification import NotificationLog

        fake_id = uuid.uuid4()
        await send_ticket_notifications(fake_id, "created", test_db)

        logs = test_db.query(NotificationLog).filter(NotificationLog.ticket_id == fake_id).all()
        assert len(logs) == 0
