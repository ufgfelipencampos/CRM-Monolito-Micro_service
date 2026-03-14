"""Testes dos endpoints de administração de papéis (roles)."""
import uuid


def _role_payload(suffix=None, permissions=None):
    s = suffix or uuid.uuid4().hex[:8]
    return {
        "name": f"role_{s}",
        "description": "Papel de teste",
        "permissions": permissions or [],
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /admin/roles
# ──────────────────────────────────────────────────────────────────────────────

async def test_create_role(client, admin_headers):
    r = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["is_active"] is True
    assert "name" in body
    assert "permissions" in body


async def test_create_role_with_all_permissions(client, admin_headers):
    payload = _role_payload(
        permissions=[
            {
                "module": "contacts",
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": True,
            }
        ]
    )
    r = await client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    assert r.status_code == 201
    perms = r.json()["permissions"]
    assert len(perms) == 1
    assert perms[0]["module"] == "contacts"
    assert perms[0]["can_create"] is True
    assert perms[0]["can_read"] is True


async def test_create_role_with_multiple_modules(client, admin_headers):
    payload = _role_payload(
        permissions=[
            {"module": "contacts", "can_create": True, "can_read": True, "can_update": False, "can_delete": False},
            {"module": "accounts", "can_create": False, "can_read": True, "can_update": False, "can_delete": False},
        ]
    )
    r = await client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    assert r.status_code == 201
    assert len(r.json()["permissions"]) == 2


async def test_create_role_duplicate_name(client, admin_headers):
    payload = _role_payload(suffix="duprole_one")
    await client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    r = await client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    assert r.status_code == 409


async def test_create_role_no_auth(client):
    r = await client.post("/api/v1/admin/roles", json=_role_payload())
    assert r.status_code == 401


async def test_create_role_no_permission(client, no_perm_headers):
    r = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /admin/roles
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_roles_returns_list(client, admin_headers):
    r = await client.get("/api/v1/admin/roles", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


async def test_list_roles_includes_default_roles(client, admin_headers):
    """O seed cria os 4 papéis padrão."""
    r = await client.get("/api/v1/admin/roles", headers=admin_headers)
    names = [role["name"] for role in r.json()]
    assert "admin" in names
    assert "manager" in names
    assert "seller" in names
    assert "viewer" in names


async def test_list_roles_shows_custom_role(client, admin_headers):
    await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    r = await client.get("/api/v1/admin/roles", headers=admin_headers)
    assert r.status_code == 200
    # Ao menos 5 papéis (4 padrão + 1 criado)
    assert len(r.json()) >= 5


async def test_list_roles_no_auth(client):
    r = await client.get("/api/v1/admin/roles")
    assert r.status_code == 401


async def test_list_roles_no_permission(client, no_perm_headers):
    r = await client.get("/api/v1/admin/roles", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /admin/roles/{role_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_role_by_id(client, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.get(f"/api/v1/admin/roles/{role_id}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == role_id


async def test_get_role_not_found(client, admin_headers):
    r = await client.get(f"/api/v1/admin/roles/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_get_role_no_auth(client, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.get(f"/api/v1/admin/roles/{role_id}")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# PUT /admin/roles/{role_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_update_role_description(client, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.put(
        f"/api/v1/admin/roles/{role_id}",
        json={"description": "Descrição atualizada"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Descrição atualizada"


async def test_update_role_replaces_all_permissions(client, admin_headers):
    """Atualizar permissões substitui completamente o conjunto anterior."""
    cr = await client.post(
        "/api/v1/admin/roles",
        json=_role_payload(
            permissions=[
                {"module": "contacts", "can_create": True, "can_read": False, "can_update": False, "can_delete": False}
            ]
        ),
        headers=admin_headers,
    )
    role_id = cr.json()["id"]

    r = await client.put(
        f"/api/v1/admin/roles/{role_id}",
        json={
            "permissions": [
                {"module": "accounts", "can_create": True, "can_read": True, "can_update": True, "can_delete": True}
            ]
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    perms = r.json()["permissions"]
    assert len(perms) == 1
    assert perms[0]["module"] == "accounts"


async def test_update_role_clear_permissions(client, admin_headers):
    cr = await client.post(
        "/api/v1/admin/roles",
        json=_role_payload(
            permissions=[
                {"module": "contacts", "can_create": True, "can_read": False, "can_update": False, "can_delete": False}
            ]
        ),
        headers=admin_headers,
    )
    role_id = cr.json()["id"]
    r = await client.put(
        f"/api/v1/admin/roles/{role_id}",
        json={"permissions": []},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["permissions"] == []


async def test_update_role_not_found(client, admin_headers):
    r = await client.put(
        f"/api/v1/admin/roles/{uuid.uuid4()}",
        json={"description": "x"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_update_role_no_permission(client, no_perm_headers, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.put(
        f"/api/v1/admin/roles/{role_id}",
        json={"description": "hackeado"},
        headers=no_perm_headers,
    )
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /admin/roles/{role_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_delete_role_soft(client, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.delete(f"/api/v1/admin/roles/{role_id}", headers=admin_headers)
    assert r.status_code == 204

    # Confirma que está desativado
    gr = await client.get(f"/api/v1/admin/roles/{role_id}", headers=admin_headers)
    assert gr.json()["is_active"] is False


async def test_delete_role_not_found(client, admin_headers):
    r = await client.delete(f"/api/v1/admin/roles/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_delete_role_no_auth(client, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.delete(f"/api/v1/admin/roles/{role_id}")
    assert r.status_code == 401


async def test_delete_role_no_permission(client, no_perm_headers, admin_headers):
    cr = await client.post("/api/v1/admin/roles", json=_role_payload(), headers=admin_headers)
    role_id = cr.json()["id"]
    r = await client.delete(f"/api/v1/admin/roles/{role_id}", headers=no_perm_headers)
    assert r.status_code == 403
