"""
Suite de testes de integração do CRM Backend.

Pré-requisito: banco de dados `crm_test` deve existir no PostgreSQL.

  psql -U postgres -c "CREATE DATABASE crm_test OWNER crm_user;"

A variável POSTGRES_DB pode ser sobrescrita antes de executar:

  POSTGRES_DB=crm_test pytest

Por padrão, as credenciais são lidas do arquivo .env (mesmo host/porta/usuário),
substituindo apenas o nome do banco.
"""
import os
import uuid
from pathlib import Path

# ── Carrega .env da raiz do projeto antes de qualquer importação do app ───────
# Necessário quando pytest é executado de dentro de tests/ ou de qualquer
# diretório que não seja a raiz, já que pydantic-settings resolve env_file
# relativo ao cwd e não encontraria o .env nesse caso.
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# Garante uso do banco de testes (sobrescreve qualquer valor anterior)
os.environ["POSTGRES_DB"] = "crm_test"

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Importações do app ocorrem APÓS definir a variável de ambiente.
from app.core.database import Base
from app.core.config import settings
from app.main import app

# Engine exclusivo para os testes (aponta para crm_test via settings).
_test_engine = create_async_engine(settings.database_url, echo=False)

# SQL para limpar todas as tabelas em cascata entre testes.
_TRUNCATE_ALL = text(
    """
    TRUNCATE TABLE
        audit_logs,
        contact_accounts,
        user_roles,
        permissions,
        password_reset_tokens,
        opportunities,
        contacts,
        accounts,
        pipeline_stages,
        users,
        roles
    RESTART IDENTITY CASCADE
    """
)


# ─── Setup do esquema (uma vez por sessão) ────────────────────────────────────

@pytest.fixture(scope="session")
async def setup_db():
    """Cria todas as tabelas no banco de testes; descarta ao final da sessão."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


# ─── Isolamento entre testes ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def truncate(setup_db):
    """Trunca todas as tabelas ANTES de cada teste para isolamento total."""
    async with _test_engine.begin() as conn:
        await conn.execute(_TRUNCATE_ALL)


# ─── Cliente HTTP ─────────────────────────────────────────────────────────────

@pytest.fixture
async def client(truncate):
    """
    AsyncClient apontado para o app com o banco de testes.
    ASGITransport não dispara eventos de lifespan, por isso o seed é chamado
    explicitamente antes de cada teste para garantir os papéis padrão e o
    usuário admin@crmapp.com.
    """
    from app.main import _seed_initial_data
    await _seed_initial_data()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ─── Headers de autenticação ──────────────────────────────────────────────────

@pytest.fixture
async def admin_headers(client):
    """Headers Bearer do admin padrão (admin@crmapp.com / Admin@1234)."""
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crmapp.com", "password": "Admin@1234"},
    )
    assert r.status_code == 200, f"Login do admin falhou: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def admin_refresh_token(client):
    """Refresh token do admin padrão."""
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crmapp.com", "password": "Admin@1234"},
    )
    assert r.status_code == 200, f"Login do admin falhou: {r.text}"
    return r.json()["refresh_token"]


@pytest.fixture
async def no_perm_headers(client, admin_headers):
    """
    Headers de um usuário autenticado mas sem nenhuma permissão.
    Útil para verificar respostas 403 nos endpoints protegidos.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"noperm_{suffix}@test.com"

    # Cria papel sem permissões
    role_resp = await client.post(
        "/api/v1/admin/roles",
        json={
            "name": f"empty_role_{suffix}",
            "description": "Papel sem permissões",
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert role_resp.status_code == 201, role_resp.text
    role_id = role_resp.json()["id"]

    # Cria usuário com esse papel
    user_resp = await client.post(
        "/api/v1/admin/users",
        json={
            "name": "Sem Permissão",
            "email": email,
            "password": "Test@1234",
            "role_ids": [role_id],
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201, user_resp.text

    # Faz login
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Test@1234"},
    )
    assert login_resp.status_code == 200, login_resp.text
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
