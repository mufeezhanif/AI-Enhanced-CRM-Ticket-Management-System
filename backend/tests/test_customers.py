def test_create_customer(client, auth_headers_manager):
    r = client.post(
        "/api/customers",
        json={"full_name": "John Doe", "email": "john@example.com"},
        headers=auth_headers_manager,
    )
    assert r.status_code == 201
    assert r.json()["full_name"] == "John Doe"


def test_get_customers_list(client, auth_headers_manager):
    client.post(
        "/api/customers",
        json={"full_name": "Jane", "email": "jane@example.com"},
        headers=auth_headers_manager,
    )
    r = client.get("/api/customers", headers=auth_headers_manager)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_search_customers(client, auth_headers_manager):
    client.post(
        "/api/customers",
        json={"full_name": "UniqueName", "email": "unique@example.com", "company": "Acme"},
        headers=auth_headers_manager,
    )
    r = client.get("/api/customers", params={"search": "UniqueName"}, headers=auth_headers_manager)
    assert r.status_code == 200
    assert any(c["full_name"] == "UniqueName" for c in r.json()["items"])


def test_update_customer(client, auth_headers_manager):
    create = client.post(
        "/api/customers",
        json={"full_name": "Update Me", "email": "update@example.com"},
        headers=auth_headers_manager,
    )
    cid = create.json()["id"]
    r = client.patch(
        f"/api/customers/{cid}",
        json={"company": "NewCo"},
        headers=auth_headers_manager,
    )
    assert r.status_code == 200
    assert r.json()["company"] == "NewCo"


def test_delete_customer_requires_manager(client, auth_headers_agent):
    create = client.post(
        "/api/customers",
        json={"full_name": "Del", "email": "del@example.com"},
        headers=auth_headers_agent,
    )
    cid = create.json()["id"]
    r = client.delete(f"/api/customers/{cid}", headers=auth_headers_agent)
    assert r.status_code == 403
