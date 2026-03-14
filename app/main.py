"""
CRM Backend - Monolito com estrutura para migração a microserviços
Fase 1 MVP: Autenticação, Contatos, Contas, Oportunidades, Pipeline
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description=(
        "CRM Backend · MVP Fase 1\n\n"
        "## Módulos disponíveis\n"
        "- **Autenticação & RBAC** — Login JWT, recuperação de senha, perfis de acesso\n"
        "- **Contatos** — CRUD de pessoas físicas / prospects\n"
        "- **Contas** — Gestão de empresas com hierarquia matriz/filial\n"
        "- **Oportunidades & Pipeline** — Funil de vendas com visualização Kanban\n"
        "- **Auditoria** — Rastreabilidade de operações críticas (NFR-003)\n"
    ),
    version="0.1.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# ──────────────── CORS ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────── Routers ────────────────
from app.modules.auth.router import router as auth_router
from app.modules.contacts.router import router as contacts_router
from app.modules.accounts.router import router as accounts_router
from app.modules.opportunities.router import router as opportunities_router
from app.modules.audit.router import router as audit_router

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(contacts_router, prefix=settings.api_prefix)
app.include_router(accounts_router, prefix=settings.api_prefix)
app.include_router(opportunities_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)


# ──────────────── Health Check ────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0", "env": settings.app_env}


@app.get(f"{settings.api_prefix}/health", tags=["Health"])
async def health_check_v1():
    return {"status": "ok", "version": "0.1.0", "env": settings.app_env}


# ──────────────── Startup ────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("Iniciando CRM Backend...")
    await _seed_initial_data()
    logger.info("CRM Backend pronto.")


async def _seed_initial_data():
    """Cria papéis padrão e usuário admin inicial se necessário."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.modules.auth.models import User, Role, RoleName
    from app.modules.auth.service import AuthService
    from app.modules.auth.schemas import UserCreate
    from app.modules.audit.service import AuditService

    async with AsyncSessionLocal() as db:
        try:
            audit = AuditService(db)
            auth = AuthService(db, audit)

            # Seed default roles
            await auth.seed_default_roles()

            # Create initial admin user if no users exist
            result = await db.execute(select(User))
            if not result.scalar_one_or_none():
                admin_role = (
                    await db.execute(select(Role).where(Role.name == RoleName.ADMIN))
                ).scalar_one_or_none()

                admin_role_id = [admin_role.id] if admin_role else []
                await auth.create_user(
                    UserCreate(
                        name="Administrador",
                        email="admin@crmapp.com",
                        password="Admin@1234",
                        role_ids=admin_role_id,
                    )
                )
                logger.info(
                    "Usuário admin padrão criado: admin@crmapp.com / Admin@1234 "
                    "— TROQUE A SENHA em produção!"
                )

            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning(f"Seed falhou (pode ser normal em primeira execução): {exc}")
