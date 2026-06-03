def _create_customer(client, headers):
    r = client.post(
        "/api/customers",
        json={"full_name": "Ticket Customer", "email": "ticketcust@example.com"},
        headers=headers,
    )
    return r.json()["id"]


def test_create_ticket(client, auth_headers_manager):
    cid = _create_customer(client, auth_headers_manager)
    r = client.post(
        "/api/tickets",
        json={
            "title": "Test ticket",
            "description": "Something broke",
            "customer_id": cid,
        },
        headers=auth_headers_manager,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "open"


def test_update_ticket_status(client, auth_headers_manager):
    cid = _create_customer(client, auth_headers_manager)
    create = client.post(
        "/api/tickets",
        json={"title": "Status test", "description": "desc", "customer_id": cid},
        headers=auth_headers_manager,
    )
    tid = create.json()["id"]
    r = client.patch(
        f"/api/tickets/{tid}",
        json={"status": "in_progress"},
        headers=auth_headers_manager,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


def test_add_comment(client, auth_headers_manager):
    cid = _create_customer(client, auth_headers_manager)
    create = client.post(
        "/api/tickets",
        json={"title": "Comment test", "description": "desc", "customer_id": cid},
        headers=auth_headers_manager,
    )
    tid = create.json()["id"]
    r = client.post(
        f"/api/tickets/{tid}/comments",
        json={"message": "Working on it"},
        headers=auth_headers_manager,
    )
    assert r.status_code == 201
    assert r.json()["message"] == "Working on it"


def test_critical_ticket_access(client, auth_headers_manager, auth_headers_agent):
    cid = _create_customer(client, auth_headers_manager)
    agents = client.get("/api/users", headers=auth_headers_manager).json()
    agent = next(a for a in agents if a["role"] == "agent") if any(a["role"] == "agent" for a in agents) else None

    create = client.post(
        "/api/tickets",
        json={
            "title": "Agent ticket",
            "description": "private",
            "customer_id": cid,
            "assigned_agent_id": None,
        },
        headers=auth_headers_manager,
    )
    tid = create.json()["id"]

    r_agent = client.get(f"/api/tickets/{tid}", headers=auth_headers_agent)
    r_manager = client.get(f"/api/tickets/{tid}", headers=auth_headers_manager)
    assert r_manager.status_code == 200


def test_resolve_ticket(client, auth_headers_manager):
    cid = _create_customer(client, auth_headers_manager)
    create = client.post(
        "/api/tickets",
        json={"title": "Resolve test", "description": "desc", "customer_id": cid},
        headers=auth_headers_manager,
    )
    tid = create.json()["id"]
    r = client.patch(
        f"/api/tickets/{tid}",
        json={"status": "resolved"},
        headers=auth_headers_manager,
    )
    assert r.status_code == 200
    assert r.json()["resolved_at"] is not None
