"""Testes dos endpoints de autenticação."""
import uuid

from jose import jwt

from app.core.config import settings


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ──────────────────────────────────────────────────────────────────────────────

async def test_login_success(client):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crmapp.com", "password": "Admin@1234"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_returns_valid_jwt_payload(client):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crmapp.com", "password": "Admin@1234"},
    )
    token = r.json()["access_token"]
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["type"] == "access"
    assert "sub" in payload
    assert "exp" in payload
    assert "email" in payload


async def test_login_wrong_password(client):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crmapp.com", "password": "WrongPass!1"},
    )
    assert r.status_code == 401


async def test_login_nonexistent_email(client):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost_nobody@nowhere.com", "password": "Admin@1234"},
    )
    assert r.status_code == 401


async def test_login_inactive_user(client, admin_headers):
    """Usuário desativado não deve conseguir fazer login."""
    email = f"inactive_{uuid.uuid4().hex[:8]}@test.com"
    cr = await client.post(
        "/api/v1/admin/users",
        json={"name": "Inactive", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = cr.json()["id"]
    await client.delete(f"/api/v1/admin/users/{user_id}", headers=admin_headers)

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Test@1234"},
    )
    assert r.status_code in (401, 403)


async def test_login_requires_form_data_not_json(client):
    """O endpoint de login exige form-data (OAuth2), não JSON."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin@crmapp.com", "password": "Admin@1234"},
    )
    assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/refresh
# ──────────────────────────────────────────────────────────────────────────────

async def test_refresh_token_success(client, admin_refresh_token):
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": admin_refresh_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_refresh_token_invalid(client):
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert r.status_code == 401


async def test_refresh_using_access_token_fails(client, admin_headers):
    """Access token não pode ser usado como refresh token."""
    access_token = admin_headers["Authorization"].split(" ")[1]
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/forgot-password
# ──────────────────────────────────────────────────────────────────────────────

async def test_forgot_password_known_email_returns_token(client):
    r = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@crmapp.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert "dev_token" in body
    assert body["dev_token"] is not None


async def test_forgot_password_unknown_email_still_returns_200(client):
    """Endereço desconhecido não deve vazar informação (anti-enumeração)."""
    r = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ghost_nobody_123@nowhere.com"},
    )
    assert r.status_code == 200
    assert "message" in r.json()


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/reset-password
# ──────────────────────────────────────────────────────────────────────────────

async def test_reset_password_success(client):
    fp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@crmapp.com"},
    )
    reset_token = fp.json()["dev_token"]

    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewPass@99"},
    )
    assert r.status_code == 204

    # Confirma login com nova senha
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crmapp.com", "password": "NewPass@99"},
    )
    assert login.status_code == 200


async def test_reset_password_invalid_token(client):
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "totally_invalid_token_xyz", "new_password": "NewPass@99"},
    )
    assert r.status_code in (400, 404)


async def test_reset_password_token_reuse_fails(client):
    """Token já utilizado não pode ser reutilizado."""
    fp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@crmapp.com"},
    )
    token = fp.json()["dev_token"]

    await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPass@99"},
    )
    # Segunda tentativa com o mesmo token
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass@88"},
    )
    assert r.status_code == 400


async def test_reset_password_weak_password_fails(client):
    """Senha fraca deve falhar na validação do schema (422)."""
    fp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@crmapp.com"},
    )
    token = fp.json()["dev_token"]
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "weak"},
    )
    assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /auth/me
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_me_authenticated(client, admin_headers):
    r = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "admin@crmapp.com"
    assert "id" in body
    assert "roles" in body
    assert "admin" in body["roles"]


async def test_get_me_unauthenticated(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_get_me_invalid_token(client):
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert r.status_code == 401


async def test_get_me_malformed_header(client):
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "NotBearer token"},
    )
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/change-password
# ──────────────────────────────────────────────────────────────────────────────

async def test_change_password_success(client, admin_headers):
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Admin@1234", "new_password": "Changed@1234"},
        headers=admin_headers,
    )
    assert r.status_code == 204


async def test_change_password_wrong_current(client, admin_headers):
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPass!9", "new_password": "Changed@1234"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_change_password_unauthenticated(client):
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Admin@1234", "new_password": "Changed@1234"},
    )
    assert r.status_code == 401


async def test_change_password_weak_new_password(client, admin_headers):
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Admin@1234", "new_password": "weak"},
        headers=admin_headers,
    )
    assert r.status_code == 422
