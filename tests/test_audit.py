"""Testes dos endpoints de auditoria."""
import uuid


# ──────────────────────────────────────────────────────────────────────────────
# GET /audit
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_audit_logs_empty(client, admin_headers):
    """Banco limpo: sem operações ainda, auditoria pode ter logs do seed."""
    r = await client.get("/api/v1/audit", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "per_page" in body
    assert "pages" in body


async def test_list_audit_logs_after_create(client, admin_headers):
    """Criação de contato deve gerar entrada na auditoria."""
    await client.post(
        "/api/v1/contacts",
        json={"name": "Audited", "email": f"aud_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/audit", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_list_audit_log_entry_structure(client, admin_headers):
    await client.post(
        "/api/v1/contacts",
        json={"name": "Struct", "email": f"struct_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/audit", headers=admin_headers)
    items = r.json()["items"]
    assert len(items) >= 1
    entry = items[0]
    for field in ("id", "entity_type", "entity_id", "action", "created_at"):
        assert field in entry


async def test_list_audit_no_auth(client):
    r = await client.get("/api/v1/audit")
    assert r.status_code == 401


async def test_list_audit_no_permission(client, no_perm_headers):
    r = await client.get("/api/v1/audit", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# Filtros
# ──────────────────────────────────────────────────────────────────────────────

async def test_audit_filter_by_entity_type_contact(client, admin_headers):
    await client.post(
        "/api/v1/contacts",
        json={"name": "FilterAudit", "email": f"fa_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/audit?entity_type=contact", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert all(i["entity_type"] == "contact" for i in items)


async def test_audit_filter_by_entity_type_account(client, admin_headers):
    await client.post(
        "/api/v1/accounts",
        json={"name": f"AuditAcc {uuid.uuid4().hex[:6]}"},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/audit?entity_type=account", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert all(i["entity_type"] == "account" for i in items)


async def test_audit_filter_by_action_create(client, admin_headers):
    await client.post(
        "/api/v1/contacts",
        json={"name": "ActionFilter", "email": f"af_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/audit?action=create", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert all(i["action"] == "create" for i in items)


async def test_audit_filter_by_entity_id(client, admin_headers):
    cp = await client.post(
        "/api/v1/contacts",
        json={"name": "EntityFilter", "email": f"ef_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    contact_id = cp.json()["id"]
    r = await client.get(f"/api/v1/audit?entity_id={contact_id}", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(str(i["entity_id"]) == contact_id for i in items)


# ──────────────────────────────────────────────────────────────────────────────
# Paginação
# ──────────────────────────────────────────────────────────────────────────────

async def test_audit_pagination(client, admin_headers):
    for i in range(4):
        await client.post(
            "/api/v1/contacts",
            json={"name": f"Bulk {i}", "email": f"bulk_{uuid.uuid4().hex[:6]}@test.com"},
            headers=admin_headers,
        )
    r = await client.get("/api/v1/audit?page=1&per_page=2", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 2
    assert body["per_page"] == 2
    assert body["page"] == 1
    assert body["pages"] >= 1


async def test_audit_second_page(client, admin_headers):
    for i in range(5):
        await client.post(
            "/api/v1/contacts",
            json={"name": f"Page {i}", "email": f"page_{uuid.uuid4().hex[:6]}@test.com"},
            headers=admin_headers,
        )
    r = await client.get("/api/v1/audit?page=2&per_page=2", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2


# ──────────────────────────────────────────────────────────────────────────────
# Rastreabilidade de operações
# ──────────────────────────────────────────────────────────────────────────────

async def test_audit_records_contact_create(client, admin_headers):
    cp = await client.post(
        "/api/v1/contacts",
        json={"name": "Traced", "email": f"traced_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    cid = cp.json()["id"]
    r = await client.get("/api/v1/audit?entity_type=contact&action=create", headers=admin_headers)
    items = r.json()["items"]
    assert any(str(i["entity_id"]) == cid for i in items)


async def test_audit_records_account_create(client, admin_headers):
    ap = await client.post(
        "/api/v1/accounts",
        json={"name": f"TracedAcc {uuid.uuid4().hex[:6]}"},
        headers=admin_headers,
    )
    aid = ap.json()["id"]
    r = await client.get("/api/v1/audit?entity_type=account&action=create", headers=admin_headers)
    items = r.json()["items"]
    assert any(str(i["entity_id"]) == aid for i in items)


async def test_audit_records_contact_deactivation(client, admin_headers):
    cp = await client.post(
        "/api/v1/contacts",
        json={"name": "Delete Log", "email": f"dl_{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers,
    )
    cid = cp.json()["id"]
    await client.delete(f"/api/v1/contacts/{cid}", headers=admin_headers)

    r = await client.get("/api/v1/audit?entity_type=contact", headers=admin_headers)
    items = r.json()["items"]
    contact_actions = [i["action"] for i in items if str(i["entity_id"]) == cid]
    assert len(contact_actions) >= 2  # create + deactivate/update


async def test_audit_records_user_creation(client, admin_headers):
    email = f"au_{uuid.uuid4().hex[:6]}@test.com"
    await client.post(
        "/api/v1/admin/users",
        json={"name": "Audited User", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/audit?entity_type=user&action=create", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1
