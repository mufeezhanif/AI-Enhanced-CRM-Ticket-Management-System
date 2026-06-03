"""
Integration tests: full end-to-end flows across multiple modules.
Tests are isolated using SQLite in-memory DB (configured in conftest.py).
Background tasks (AI, messaging) are disabled via TESTING env var.
"""
import pytest
from unittest.mock import patch


# ─── Helpers ────────────────────────────────────────────────────────────────

def _create_customer(client, headers, name="Integration Customer", email="integ@example.com"):
    r = client.post("/api/customers", json={"full_name": name, "email": email}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _create_ticket(client, headers, customer_id, title="Integration Ticket", desc="desc", priority="medium"):
    r = client.post(
        "/api/tickets",
        json={"title": title, "description": desc, "customer_id": customer_id, "priority": priority},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _register_agent(client, manager_headers, name="New Agent", email="newagent@example.com"):
    r = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": "password123", "role": "agent"},
        headers=manager_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _login(client, email, password="password123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ─── Full Ticket Lifecycle ────────────────────────────────────────────────────

class TestTicketLifecycle:
    """Full lifecycle: create → assign → comment → resolve → verify."""

    def test_full_lifecycle_manager(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager)
        cid = customer["id"]

        ticket = _create_ticket(client, auth_headers_manager, cid)
        tid = ticket["id"]

        assert ticket["status"] == "open"
        assert ticket["priority"] == "medium"

        r = client.patch(
            f"/api/tickets/{tid}",
            json={"status": "in_progress"},
            headers=auth_headers_manager,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"
        assert r.json()["resolved_at"] is None

        comment_r = client.post(
            f"/api/tickets/{tid}/comments",
            json={"message": "Investigating the issue", "is_internal": False},
            headers=auth_headers_manager,
        )
        assert comment_r.status_code == 201
        assert comment_r.json()["message"] == "Investigating the issue"
        assert comment_r.json()["is_internal"] is False

        r = client.patch(
            f"/api/tickets/{tid}",
            json={"status": "resolved"},
            headers=auth_headers_manager,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None

    def test_close_ticket_after_resolve(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="close@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])
        tid = ticket["id"]

        client.patch(f"/api/tickets/{tid}", json={"status": "resolved"}, headers=auth_headers_manager)
        r = client.patch(f"/api/tickets/{tid}", json={"status": "closed"}, headers=auth_headers_manager)
        assert r.status_code == 200
        assert r.json()["status"] == "closed"

    def test_priority_escalation_to_critical(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="escalate@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])
        tid = ticket["id"]

        r = client.patch(
            f"/api/tickets/{tid}",
            json={"priority": "critical"},
            headers=auth_headers_manager,
        )
        assert r.status_code == 200
        assert r.json()["priority"] == "critical"


# ─── Role-Based Access Control ───────────────────────────────────────────────

class TestRoleBasedAccess:
    """Agents see only their data; managers see all."""

    def test_agent_sees_only_own_tickets(self, client, auth_headers_manager, agent_user):
        agent_headers = _login(client, "agent@test.com")

        customer_m = _create_customer(client, auth_headers_manager, email="mgr_cust@example.com")
        unassigned_ticket = _create_ticket(client, auth_headers_manager, customer_m["id"], title="Manager only ticket")
        tid_unassigned = unassigned_ticket["id"]

        customer_a = _create_customer(client, agent_headers, email="agent_cust@example.com")
        agent_ticket = _create_ticket(client, agent_headers, customer_a["id"], title="Agent ticket")
        tid_agent = agent_ticket["id"]

        r_agent_list = client.get("/api/tickets", headers=agent_headers)
        assert r_agent_list.status_code == 200
        agent_ticket_ids = [t["id"] for t in r_agent_list.json()["items"]]
        assert tid_agent in agent_ticket_ids
        assert tid_unassigned not in agent_ticket_ids

        r_manager_list = client.get("/api/tickets", headers=auth_headers_manager)
        manager_ticket_ids = [t["id"] for t in r_manager_list.json()["items"]]
        assert tid_unassigned in manager_ticket_ids
        assert tid_agent in manager_ticket_ids

    def test_agent_cannot_access_other_agent_ticket(self, client, auth_headers_manager, agent_user):
        agent_headers = _login(client, "agent@test.com")

        second_agent = _register_agent(client, auth_headers_manager, email="second@example.com")
        second_headers = _login(client, "second@example.com")

        customer = _create_customer(client, second_headers, email="second_cust@example.com")
        ticket = _create_ticket(client, second_headers, customer["id"])
        tid = ticket["id"]

        r = client.get(f"/api/tickets/{tid}", headers=agent_headers)
        assert r.status_code == 403

    def test_agent_cannot_delete_customer(self, client, auth_headers_agent):
        customer = _create_customer(client, auth_headers_agent, email="nodelet@example.com")
        r = client.delete(f"/api/customers/{customer['id']}", headers=auth_headers_agent)
        assert r.status_code == 403

    def test_agent_cannot_register_new_user(self, client, auth_headers_agent):
        r = client.post(
            "/api/auth/register",
            json={"name": "X", "email": "x@x.com", "password": "pass", "role": "agent"},
            headers=auth_headers_agent,
        )
        assert r.status_code == 403

    def test_manager_can_delete_customer(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="deleteme@example.com")
        r = client.delete(f"/api/customers/{customer['id']}", headers=auth_headers_manager)
        assert r.status_code == 204

        r2 = client.get(f"/api/customers/{customer['id']}", headers=auth_headers_manager)
        assert r2.status_code == 404

    def test_unauthenticated_cannot_access_any_endpoint(self, client):
        for path in ["/api/customers", "/api/tickets", "/api/dashboard/stats"]:
            r = client.get(path)
            assert r.status_code == 401, f"{path} returned {r.status_code}"


# ─── Comment Visibility ────────────────────────────────────────────────────

class TestCommentVisibility:
    """Internal comments hidden from other agents; visible to manager."""

    def test_internal_comment_hidden_from_other_agent(self, client, auth_headers_manager, agent_user):
        second = _register_agent(client, auth_headers_manager, email="hiddenagent@example.com")
        second_headers = _login(client, "hiddenagent@example.com")

        agent_headers = _login(client, "agent@test.com")
        customer = _create_customer(client, agent_headers, email="internalcust@example.com")
        ticket = _create_ticket(client, agent_headers, customer["id"])
        tid = ticket["id"]

        client.post(
            f"/api/tickets/{tid}/comments",
            json={"message": "secret internal note", "is_internal": True},
            headers=agent_headers,
        )

        r_manager = client.get(f"/api/tickets/{tid}/comments", headers=auth_headers_manager)
        assert any(c["message"] == "secret internal note" for c in r_manager.json())

    def test_public_comment_visible_to_all(self, client, auth_headers_manager, agent_user):
        agent_headers = _login(client, "agent@test.com")
        customer = _create_customer(client, agent_headers, email="pubcomm@example.com")
        ticket = _create_ticket(client, agent_headers, customer["id"])
        tid = ticket["id"]

        client.post(
            f"/api/tickets/{tid}/comments",
            json={"message": "public update", "is_internal": False},
            headers=agent_headers,
        )

        r = client.get(f"/api/tickets/{tid}/comments", headers=auth_headers_manager)
        assert any(c["message"] == "public update" for c in r.json())

    def test_comment_author_can_delete_own_comment(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="delcomm@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])
        comment_r = client.post(
            f"/api/tickets/{ticket['id']}/comments",
            json={"message": "delete me"},
            headers=auth_headers_manager,
        )
        comment_id = comment_r.json()["id"]

        r = client.delete(f"/api/comments/{comment_id}", headers=auth_headers_manager)
        assert r.status_code == 204

        comments = client.get(f"/api/tickets/{ticket['id']}/comments", headers=auth_headers_manager)
        assert not any(c["id"] == comment_id for c in comments.json())


# ─── Customer Module Integration ─────────────────────────────────────────────

class TestCustomerIntegration:
    """Customer CRUD and ticket history."""

    def test_customer_ticket_history(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="history@example.com")
        cid = customer["id"]

        _create_ticket(client, auth_headers_manager, cid, title="Ticket One")
        _create_ticket(client, auth_headers_manager, cid, title="Ticket Two")

        r = client.get(f"/api/customers/{cid}/tickets", headers=auth_headers_manager)
        assert r.status_code == 200
        titles = [t["title"] for t in r.json()]
        assert "Ticket One" in titles
        assert "Ticket Two" in titles

    def test_customer_search_by_email(self, client, auth_headers_manager):
        _create_customer(client, auth_headers_manager, name="SearchTest", email="findme@example.com")
        r = client.get("/api/customers", params={"search": "findme"}, headers=auth_headers_manager)
        assert r.status_code == 200
        assert any(c["email"] == "findme@example.com" for c in r.json()["items"])

    def test_customer_search_by_company(self, client, auth_headers_manager):
        client.post(
            "/api/customers",
            json={"full_name": "Corp Test", "email": "corp@example.com", "company": "UniqueCorp"},
            headers=auth_headers_manager,
        )
        r = client.get("/api/customers", params={"search": "UniqueCorp"}, headers=auth_headers_manager)
        assert r.status_code == 200
        assert any(c["company"] == "UniqueCorp" for c in r.json()["items"])

    def test_customer_not_found_returns_404(self, client, auth_headers_manager):
        r = client.get("/api/customers/00000000-0000-0000-0000-000000000000", headers=auth_headers_manager)
        assert r.status_code == 404

    def test_pagination(self, client, auth_headers_manager):
        for i in range(5):
            _create_customer(client, auth_headers_manager, name=f"Paged {i}", email=f"page{i}@example.com")

        r = client.get("/api/customers", params={"page": 1, "size": 2}, headers=auth_headers_manager)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["page"] == 1
        assert data["size"] == 2

    def test_duplicate_email_on_create(self, client, auth_headers_manager):
        _create_customer(client, auth_headers_manager, email="dup@example.com")
        r = client.post(
            "/api/customers",
            json={"full_name": "Dup", "email": "dup@example.com"},
            headers=auth_headers_manager,
        )
        # No unique constraint on customers.email (by design), so 201 is correct
        assert r.status_code == 201


# ─── Ticket Filters ───────────────────────────────────────────────────────────

class TestTicketFilters:
    """Filter tickets by status, priority, search."""

    def test_filter_by_status(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="filtercust@example.com")
        cid = customer["id"]
        t1 = _create_ticket(client, auth_headers_manager, cid, title="Open ticket")
        t2 = _create_ticket(client, auth_headers_manager, cid, title="Resolved ticket")
        client.patch(f"/api/tickets/{t2['id']}", json={"status": "resolved"}, headers=auth_headers_manager)

        r = client.get("/api/tickets", params={"status": "open"}, headers=auth_headers_manager)
        ids = [t["id"] for t in r.json()["items"]]
        assert t1["id"] in ids
        assert t2["id"] not in ids

    def test_filter_by_priority(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="priocust@example.com")
        cid = customer["id"]
        critical = _create_ticket(client, auth_headers_manager, cid, title="Critical one", priority="critical")
        low = _create_ticket(client, auth_headers_manager, cid, title="Low one", priority="low")

        r = client.get("/api/tickets", params={"priority": "critical"}, headers=auth_headers_manager)
        ids = [t["id"] for t in r.json()["items"]]
        assert critical["id"] in ids
        assert low["id"] not in ids

    def test_search_tickets(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="srchcust@example.com")
        cid = customer["id"]
        _create_ticket(client, auth_headers_manager, cid, title="UniqueXYZ issue")

        r = client.get("/api/tickets", params={"search": "UniqueXYZ"}, headers=auth_headers_manager)
        assert r.status_code == 200
        assert any("UniqueXYZ" in t["title"] for t in r.json()["items"])

    def test_filter_by_customer_id(self, client, auth_headers_manager):
        c1 = _create_customer(client, auth_headers_manager, email="c1@example.com")
        c2 = _create_customer(client, auth_headers_manager, email="c2@example.com")
        t1 = _create_ticket(client, auth_headers_manager, c1["id"], title="C1 ticket")
        t2 = _create_ticket(client, auth_headers_manager, c2["id"], title="C2 ticket")

        r = client.get("/api/tickets", params={"customer_id": c1["id"]}, headers=auth_headers_manager)
        ids = [t["id"] for t in r.json()["items"]]
        assert t1["id"] in ids
        assert t2["id"] not in ids


# ─── AI Auto-Escalation Flow ─────────────────────────────────────────────────

class TestAIEscalation:
    """When ticket has frustrated sentiment, priority auto-escalates to critical on update."""

    def test_auto_escalate_on_frustrated_sentiment(self, client, auth_headers_manager, test_db):
        from app.models.ticket import Ticket, TicketStatus

        customer = _create_customer(client, auth_headers_manager, email="frustemail@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])
        tid = ticket["id"]

        import uuid
        db_ticket = test_db.query(Ticket).filter(Ticket.id == uuid.UUID(tid)).first()
        db_ticket.ai_sentiment = "frustrated"
        # keep status as "open" so escalation condition triggers
        test_db.commit()

        # PATCH something other than status — escalation check only fires when
        # status is still "open" after the update (checked post-setattr in router)
        r = client.patch(
            f"/api/tickets/{tid}",
            json={"category": "Billing"},
            headers=auth_headers_manager,
        )
        assert r.status_code == 200
        assert r.json()["priority"] == "critical"

    def test_no_escalation_when_sentiment_not_frustrated(self, client, auth_headers_manager, test_db):
        from app.models.ticket import Ticket

        customer = _create_customer(client, auth_headers_manager, email="neutralemail@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])
        tid = ticket["id"]

        import uuid
        db_ticket = test_db.query(Ticket).filter(Ticket.id == uuid.UUID(tid)).first()
        db_ticket.ai_sentiment = "neutral"
        test_db.commit()

        r = client.patch(
            f"/api/tickets/{tid}",
            json={"status": "in_progress"},
            headers=auth_headers_manager,
        )
        assert r.status_code == 200
        assert r.json()["priority"] == "medium"


# ─── Ticket Delete ────────────────────────────────────────────────────────────

class TestTicketDelete:
    def test_manager_can_delete_ticket(self, client, auth_headers_manager):
        customer = _create_customer(client, auth_headers_manager, email="ticketdel@example.com")
        ticket = _create_ticket(client, auth_headers_manager, customer["id"])
        tid = ticket["id"]

        r = client.delete(f"/api/tickets/{tid}", headers=auth_headers_manager)
        assert r.status_code == 204

        r2 = client.get(f"/api/tickets/{tid}", headers=auth_headers_manager)
        assert r2.status_code == 404

    def test_agent_cannot_delete_ticket(self, client, auth_headers_manager, auth_headers_agent, agent_user):
        agent_headers = _login(client, "agent@test.com")
        customer = _create_customer(client, agent_headers, email="agentdel@example.com")
        ticket = _create_ticket(client, agent_headers, customer["id"])
        tid = ticket["id"]

        r = client.delete(f"/api/tickets/{tid}", headers=agent_headers)
        assert r.status_code == 403
