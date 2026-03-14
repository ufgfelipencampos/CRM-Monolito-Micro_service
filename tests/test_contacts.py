"""Testes dos endpoints de contatos."""
import uuid


def _contact_payload(suffix=None, **extra):
    s = suffix or uuid.uuid4().hex[:8]
    return {
        "name": f"Contact {s}",
        "email": f"contact_{s}@example.com",
        "phone": "+5511999990000",
        "cargo": "Analista",
        "lead_source": "website",
        "tags": ["lead", "vip"],
        "notes": "Nota de teste",
        **extra,
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /contacts
# ──────────────────────────────────────────────────────────────────────────────

async def test_create_contact(client, admin_headers):
    r = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["is_active"] is True


async def test_create_contact_response_structure(client, admin_headers):
    r = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    for field in ("id", "name", "email", "is_active", "accounts", "created_at"):
        assert field in body


async def test_create_contact_minimal_payload(client, admin_headers):
    """Apenas name e email são obrigatórios."""
    suffix = uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/contacts",
        json={"name": f"Min {suffix}", "email": f"min_{suffix}@test.com"},
        headers=admin_headers,
    )
    assert r.status_code == 201


async def test_create_contact_no_auth(client):
    r = await client.post("/api/v1/contacts", json=_contact_payload())
    assert r.status_code == 401


async def test_create_contact_no_permission(client, no_perm_headers):
    r = await client.post("/api/v1/contacts", json=_contact_payload(), headers=no_perm_headers)
    assert r.status_code == 403


async def test_create_contact_invalid_email(client, admin_headers):
    r = await client.post(
        "/api/v1/contacts",
        json={"name": "Bad Email", "email": "not-valid"},
        headers=admin_headers,
    )
    assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /contacts
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_contacts_empty(client, admin_headers):
    r = await client.get("/api/v1/contacts", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 0


async def test_list_contacts_returns_created(client, admin_headers):
    await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    r = await client.get("/api/v1/contacts", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_list_contacts_pagination_structure(client, admin_headers):
    for _ in range(3):
        await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    r = await client.get("/api/v1/contacts?page=1&per_page=2", headers=admin_headers)
    body = r.json()
    assert body["page"] == 1
    assert body["per_page"] == 2
    assert len(body["items"]) <= 2


async def test_list_contacts_filter_by_name(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    name = f"Filterable {suffix}"
    await client.post(
        "/api/v1/contacts",
        json=_contact_payload(suffix=suffix, name=name),
        headers=admin_headers,
    )
    r = await client.get(f"/api/v1/contacts?name={name}", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(item["name"] == name for item in items)


async def test_list_contacts_filter_by_email(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    email = f"searchable_{suffix}@example.com"
    await client.post(
        "/api/v1/contacts",
        json=_contact_payload(suffix=suffix, email=email),
        headers=admin_headers,
    )
    r = await client.get(f"/api/v1/contacts?email={email}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_list_contacts_excludes_inactive_by_default(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    await client.delete(f"/api/v1/contacts/{cid}", headers=admin_headers)

    r = await client.get("/api/v1/contacts", headers=admin_headers)
    ids = [i["id"] for i in r.json()["items"]]
    assert cid not in ids


async def test_list_contacts_filter_inactive(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    await client.delete(f"/api/v1/contacts/{cid}", headers=admin_headers)

    r = await client.get("/api/v1/contacts?is_active=false", headers=admin_headers)
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()["items"]]
    assert cid in ids


async def test_list_contacts_no_auth(client):
    r = await client.get("/api/v1/contacts")
    assert r.status_code == 401


async def test_list_contacts_no_permission(client, no_perm_headers):
    r = await client.get("/api/v1/contacts", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /contacts/{contact_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_contact_by_id(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.get(f"/api/v1/contacts/{cid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == cid


async def test_get_contact_not_found(client, admin_headers):
    r = await client.get(f"/api/v1/contacts/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_get_contact_no_auth(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.get(f"/api/v1/contacts/{cid}")
    assert r.status_code == 401


async def test_get_contact_no_permission(client, no_perm_headers, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.get(f"/api/v1/contacts/{cid}", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# PUT /contacts/{contact_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_update_contact(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.put(
        f"/api/v1/contacts/{cid}",
        json={"name": "Updated Name", "cargo": "Gerente"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"
    assert r.json()["cargo"] == "Gerente"


async def test_update_contact_tags(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.put(
        f"/api/v1/contacts/{cid}",
        json={"tags": ["hot", "enterprise"]},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert "hot" in r.json()["tags"]


async def test_update_contact_not_found(client, admin_headers):
    r = await client.put(
        f"/api/v1/contacts/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_update_contact_no_auth(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.put(f"/api/v1/contacts/{cid}", json={"name": "Anon"})
    assert r.status_code == 401


async def test_update_contact_no_permission(client, no_perm_headers, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.put(
        f"/api/v1/contacts/{cid}",
        json={"name": "Hacked"},
        headers=no_perm_headers,
    )
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /contacts/{contact_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_deactivate_contact(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.delete(f"/api/v1/contacts/{cid}", headers=admin_headers)
    assert r.status_code == 204


async def test_deactivate_contact_not_found(client, admin_headers):
    r = await client.delete(f"/api/v1/contacts/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_deactivate_contact_already_inactive(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    await client.delete(f"/api/v1/contacts/{cid}", headers=admin_headers)
    r = await client.delete(f"/api/v1/contacts/{cid}", headers=admin_headers)
    assert r.status_code == 400


async def test_deactivate_contact_no_auth(client, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.delete(f"/api/v1/contacts/{cid}")
    assert r.status_code == 401


async def test_deactivate_contact_no_permission(client, no_perm_headers, admin_headers):
    cp = await client.post("/api/v1/contacts", json=_contact_payload(), headers=admin_headers)
    cid = cp.json()["id"]
    r = await client.delete(f"/api/v1/contacts/{cid}", headers=no_perm_headers)
    assert r.status_code == 403
