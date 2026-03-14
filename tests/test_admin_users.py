"""Testes dos endpoints de administração de usuários."""
import uuid


# ──────────────────────────────────────────────────────────────────────────────
# POST /admin/users
# ──────────────────────────────────────────────────────────────────────────────

async def test_create_user(client, admin_headers):
    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    r = await client.post(
        "/api/v1/admin/users",
        json={"name": "Test User", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == email
    assert body["name"] == "Test User"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


async def test_create_user_response_structure(client, admin_headers):
    email = f"struct_{uuid.uuid4().hex[:8]}@test.com"
    r = await client.post(
        "/api/v1/admin/users",
        json={"name": "Structured", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    assert r.status_code == 201
    body = r.json()
    for field in ("id", "name", "email", "is_active", "roles", "created_at"):
        assert field in body


async def test_create_user_with_role(client, admin_headers):
    role_r = await client.post(
        "/api/v1/admin/roles",
        json={"name": f"role_{uuid.uuid4().hex[:6]}", "description": "x", "permissions": []},
        headers=admin_headers,
    )
    role_id = role_r.json()["id"]
    email = f"withrole_{uuid.uuid4().hex[:6]}@test.com"
    r = await client.post(
        "/api/v1/admin/users",
        json={"name": "Com Papel", "email": email, "password": "Test@1234", "role_ids": [role_id]},
        headers=admin_headers,
    )
    assert r.status_code == 201
    assert len(r.json()["roles"]) >= 1


async def test_create_user_duplicate_email(client, admin_headers):
    email = f"dup_{uuid.uuid4().hex[:8]}@test.com"
    payload = {"name": "Dup", "email": email, "password": "Test@1234", "role_ids": []}
    await client.post("/api/v1/admin/users", json=payload, headers=admin_headers)
    r = await client.post("/api/v1/admin/users", json=payload, headers=admin_headers)
    assert r.status_code == 409


async def test_create_user_unauthenticated(client):
    r = await client.post(
        "/api/v1/admin/users",
        json={"name": "X", "email": "x@x.com", "password": "Test@1234", "role_ids": []},
    )
    assert r.status_code == 401


async def test_create_user_no_permission(client, no_perm_headers):
    r = await client.post(
        "/api/v1/admin/users",
        json={"name": "X", "email": "x2@x.com", "password": "Test@1234", "role_ids": []},
        headers=no_perm_headers,
    )
    assert r.status_code == 403


async def test_create_user_invalid_email(client, admin_headers):
    r = await client.post(
        "/api/v1/admin/users",
        json={"name": "Bad", "email": "not-an-email", "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /admin/users
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_users_returns_paginated_response(client, admin_headers):
    r = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "per_page" in body
    assert "pages" in body
    assert body["total"] >= 1  # ao menos o admin semeado


async def test_list_users_includes_seeded_admin(client, admin_headers):
    r = await client.get("/api/v1/admin/users", headers=admin_headers)
    emails = [u["email"] for u in r.json()["items"]]
    assert "admin@crmapp.com" in emails


async def test_list_users_pagination(client, admin_headers):
    for i in range(3):
        await client.post(
            "/api/v1/admin/users",
            json={
                "name": f"Paged {i}",
                "email": f"paged_{uuid.uuid4().hex[:6]}@test.com",
                "password": "Test@1234",
                "role_ids": [],
            },
            headers=admin_headers,
        )
    r = await client.get("/api/v1/admin/users?page=1&per_page=2", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 2
    assert body["per_page"] == 2
    assert body["page"] == 1


async def test_list_users_no_auth(client):
    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 401


async def test_list_users_no_permission(client, no_perm_headers):
    r = await client.get("/api/v1/admin/users", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /admin/users/{user_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_user_by_id(client, admin_headers):
    email = f"get_{uuid.uuid4().hex[:8]}@test.com"
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "Get Me", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.get(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == user_id
    assert r.json()["email"] == email


async def test_get_user_not_found(client, admin_headers):
    r = await client.get(f"/api/v1/admin/users/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_get_user_no_auth(client, admin_headers):
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "X", "email": f"x_{uuid.uuid4().hex[:6]}@test.com", "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.get(f"/api/v1/admin/users/{user_id}")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# PUT /admin/users/{user_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_update_user_name(client, admin_headers):
    email = f"upd_{uuid.uuid4().hex[:8]}@test.com"
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "Before", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"name": "After"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "After"


async def test_update_user_add_role(client, admin_headers):
    email = f"addrole_{uuid.uuid4().hex[:6]}@test.com"
    role_r = await client.post(
        "/api/v1/admin/roles",
        json={"name": f"r_{uuid.uuid4().hex[:6]}", "description": "x", "permissions": []},
        headers=admin_headers,
    )
    role_id = role_r.json()["id"]
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "No Role", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"role_ids": [role_id]},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert len(r.json()["roles"]) >= 1


async def test_update_user_not_found(client, admin_headers):
    r = await client.put(
        f"/api/v1/admin/users/{uuid.uuid4()}",
        json={"name": "X"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_update_user_no_permission(client, no_perm_headers, admin_headers):
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "Target", "email": f"t_{uuid.uuid4().hex[:6]}@test.com", "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"name": "Hacked"},
        headers=no_perm_headers,
    )
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /admin/users/{user_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_deactivate_user(client, admin_headers):
    email = f"del_{uuid.uuid4().hex[:8]}@test.com"
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "To Deactivate", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.delete(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert r.status_code == 204

    # Confirma que está desativado
    gr = await client.get(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert gr.json()["is_active"] is False


async def test_deactivated_user_cannot_login(client, admin_headers):
    email = f"deact_{uuid.uuid4().hex[:8]}@test.com"
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "Will Deactivate", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    await client.delete(f"/api/v1/admin/users/{user_id}", headers=admin_headers)

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Test@1234"},
    )
    assert r.status_code in (401, 403)


async def test_deactivate_user_not_found(client, admin_headers):
    r = await client.delete(f"/api/v1/admin/users/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_deactivate_user_no_auth(client, admin_headers):
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "X", "email": f"x_{uuid.uuid4().hex[:6]}@test.com", "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    r = await client.delete(f"/api/v1/admin/users/{user_id}")
    assert r.status_code == 401
