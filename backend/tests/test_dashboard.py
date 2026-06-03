"""
Dashboard endpoint tests: stats correctness, agent workloads, role restrictions.
"""
from datetime import datetime, timedelta


def _create_customer(client, headers, email):
    r = client.post("/api/customers", json={"full_name": "Dash Cust", "email": email}, headers=headers)
    assert r.status_code == 201
    return r.json()


def _create_ticket(client, headers, customer_id, priority="medium", title="Dash Ticket"):
    r = client.post(
        "/api/tickets",
        json={"title": title, "description": "desc", "customer_id": customer_id, "priority": priority},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


class TestDashboardStats:
    def test_stats_returns_required_keys(self, client, auth_headers_manager):
        r = client.get("/api/dashboard/stats", headers=auth_headers_manager)
        assert r.status_code == 200
        data = r.json()
        required = ["total_open", "resolved_today", "critical_tickets", "total_customers",
                    "tickets_by_status", "tickets_by_priority"]
        for key in required:
            assert key in data, f"Missing key: {key}"

    def test_stats_counts_open_tickets(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, "stats_open@example.com")
        _create_ticket(client, auth_headers_manager, customer["id"])
        _create_ticket(client, auth_headers_manager, customer["id"])

        r = client.get("/api/dashboard/stats", headers=auth_headers_manager)
        assert r.json()["total_open"] >= 2

    def test_stats_counts_critical_tickets(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, "stats_crit@example.com")
        t = _create_ticket(client, auth_headers_manager, customer["id"], priority="critical")

        r = client.get("/api/dashboard/stats", headers=auth_headers_manager)
        assert r.json()["critical_tickets"] >= 1

    def test_stats_counts_customers(self, client, auth_headers_manager):
        _create_customer(client, auth_headers_manager, "dashcust1@example.com")
        _create_customer(client, auth_headers_manager, "dashcust2@example.com")

        r = client.get("/api/dashboard/stats", headers=auth_headers_manager)
        assert r.json()["total_customers"] >= 2

    def test_stats_tickets_by_status_has_all_statuses(self, client, auth_headers_manager):
        r = client.get("/api/dashboard/stats", headers=auth_headers_manager)
        by_status = r.json()["tickets_by_status"]
        for status in ["open", "in_progress", "resolved", "closed"]:
            assert status in by_status

    def test_stats_tickets_by_priority_has_all_priorities(self, client, auth_headers_manager):
        r = client.get("/api/dashboard/stats", headers=auth_headers_manager)
        by_priority = r.json()["tickets_by_priority"]
        for priority in ["low", "medium", "high", "critical"]:
            assert priority in by_priority

    def test_resolved_today_increments_on_resolve(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, "restoday@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])

        before = client.get("/api/dashboard/stats", headers=auth_headers_manager).json()["resolved_today"]

        client.patch(f"/api/tickets/{ticket['id']}", json={"status": "resolved"}, headers=auth_headers_manager)

        after = client.get("/api/dashboard/stats", headers=auth_headers_manager).json()["resolved_today"]
        assert after == before + 1

    def test_stats_accessible_by_agent(self, client, auth_headers_agent):
        r = client.get("/api/dashboard/stats", headers=auth_headers_agent)
        assert r.status_code == 200

    def test_stats_unauthenticated_returns_401(self, client):
        r = client.get("/api/dashboard/stats")
        assert r.status_code == 401


class TestAgentWorkloads:
    def test_workloads_manager_only(self, client, auth_headers_agent):
        r = client.get("/api/dashboard/agent-workloads", headers=auth_headers_agent)
        assert r.status_code == 403

    def test_workloads_returns_list(self, client, auth_headers_manager):
        r = client.get("/api/dashboard/agent-workloads", headers=auth_headers_manager)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_workloads_contains_agent_data(self, client, auth_headers_manager, agent_user):
        customer = _create_customer(client, auth_headers_manager, "workload@example.com")
        client.post(
            "/api/tickets",
            json={
                "title": "Workload ticket",
                "description": "desc",
                "customer_id": customer["id"],
                "assigned_agent_id": str(agent_user.id),
            },
            headers=auth_headers_manager,
        )

        r = client.get("/api/dashboard/agent-workloads", headers=auth_headers_manager)
        agents = r.json()
        matching = [a for a in agents if str(a["agent_id"]) == str(agent_user.id)]
        assert len(matching) == 1
        assert matching[0]["total"] >= 1

    def test_workloads_required_keys(self, client, auth_headers_manager, agent_user):
        r = client.get("/api/dashboard/agent-workloads", headers=auth_headers_manager)
        assert r.status_code == 200
        if r.json():
            entry = r.json()[0]
            for key in ["agent_id", "agent_name", "total", "open", "in_progress", "resolved_this_week"]:
                assert key in entry


class TestRecentNotifications:
    def test_notifications_manager_only(self, client, auth_headers_agent):
        r = client.get("/api/dashboard/notifications", headers=auth_headers_agent)
        assert r.status_code == 403

    def test_notifications_returns_list(self, client, auth_headers_manager):
        r = client.get("/api/dashboard/notifications", headers=auth_headers_manager)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_notification_log_appears_in_dashboard(self, client, auth_headers_manager, test_db):
        from app.models.notification import NotificationLog
        from app.models.customer import Customer
        from app.models.ticket import Ticket
        from app.models.user import User, UserRole
        from app.dependencies import get_password_hash
        from uuid import uuid4

        user = User(
            name="DashNotifUser",
            email="dashnotif@test.com",
            password_hash=get_password_hash("pass"),
            role=UserRole.manager,
        )
        test_db.add(user)
        test_db.flush()

        customer = Customer(full_name="DashNotifCust", email="dashnotifcust@test.com", created_at=datetime.utcnow())
        test_db.add(customer)
        test_db.flush()

        ticket = Ticket(
            title="DashNotif Ticket",
            description="desc",
            customer_id=customer.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_db.add(ticket)
        test_db.flush()

        log = NotificationLog(
            id=uuid4(),
            ticket_id=ticket.id,
            platform="email",
            message="Test dashboard notification",
            status="sent",
            sent_at=datetime.utcnow(),
        )
        test_db.add(log)
        test_db.commit()

        r = client.get("/api/dashboard/notifications", headers=auth_headers_manager)
        assert r.status_code == 200
        ids = [n["id"] for n in r.json()]
        assert str(log.id) in ids
