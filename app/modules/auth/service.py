import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
)
from app.core.config import settings
from app.modules.auth.models import User, Role, Permission, PasswordResetToken, RoleName
from app.modules.auth.schemas import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserUpdate,
    RoleCreate,
    RoleUpdate,
)
from app.modules.audit.service import AuditService


class AuthService:
    def __init__(self, db: AsyncSession, audit: AuditService):
        self.db = db
        self.audit = audit

    # ──────────────── Login ────────────────

    async def login(
        self,
        data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        result = await self.db.execute(
            select(User)
            .where(User.email == data.email.lower())
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            entity_id = user.id if user else uuid.uuid4()
            await self.audit.log(
                entity_type="user",
                entity_id=entity_id,
                action="login_failed",
                ip_address=ip_address,
                user_agent=user_agent,
                new_values={"email": data.email},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha inválidos",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo",
            )

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="login",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh inválido ou expirado",
        )
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise credentials_exception
            user_id: str = payload.get("sub")
            if not user_id:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise credentials_exception

        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    # ──────────────── Password Reset ────────────────

    async def forgot_password(self, email: str) -> str:
        """Returns the reset token (in production, send via email)."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        # Always return success to avoid user enumeration
        if not user or not user.is_active:
            return "Se o e-mail existir, um link será enviado"

        token_str = generate_reset_token()
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_rate_limit_minutes
        )
        reset_token = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token=token_str,
            expires_at=expires,
        )
        self.db.add(reset_token)
        await self.db.flush()

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="password_reset_requested",
            new_values={"email": email},
        )
        # In production: send email with token
        return token_str

    async def reset_password(self, token: str, new_password: str) -> None:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token or reset_token.used_at is not None:
            raise HTTPException(status_code=400, detail="Token inválido ou já utilizado")

        if reset_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token expirado")

        result = await self.db.execute(
            select(User).where(User.id == reset_token.user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        user.password_hash = hash_password(new_password)
        reset_token.used_at = datetime.now(timezone.utc)

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="password_reset",
        )

    # ──────────────── Users ────────────────

    async def create_user(self, data: UserCreate, creator_id: Optional[UUID] = None) -> User:
        result = await self.db.execute(select(User).where(User.email == data.email.lower()))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="E-mail já cadastrado")

        user = User(
            id=uuid.uuid4(),
            name=data.name,
            email=data.email.lower(),
            password_hash=hash_password(data.password),
        )
        if data.role_ids:
            roles_result = await self.db.execute(
                select(Role).where(Role.id.in_(data.role_ids), Role.is_active == True)
            )
            user.roles = list(roles_result.scalars().all())
        else:
            user.roles = []

        self.db.add(user)
        await self.db.flush()

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="create",
            user_id=creator_id,
            new_values={"name": user.name, "email": user.email},
        )
        return user

    async def get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return user

    async def list_users(self, page: int = 1, per_page: int = 20):
        from app.shared.pagination import PaginationParams
        params = PaginationParams(page=page, per_page=per_page)
        q = select(User).options(selectinload(User.roles))
        count = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.offset(params.offset).limit(params.per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), count

    async def update_user(
        self, user_id: UUID, data: UserUpdate, updater_id: Optional[UUID] = None
    ) -> User:
        user = await self.get_user(user_id)
        old = {"name": user.name, "email": user.email, "is_active": user.is_active}

        if data.name is not None:
            user.name = data.name
        if data.email is not None:
            user.email = data.email.lower()
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.role_ids is not None:
            roles_result = await self.db.execute(
                select(Role).where(Role.id.in_(data.role_ids), Role.is_active == True)
            )
            user.roles = list(roles_result.scalars().all())

        await self.db.flush()
        await self.db.refresh(user)
        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="update",
            user_id=updater_id,
            old_values=old,
            new_values={"name": user.name, "email": user.email, "is_active": user.is_active},
        )
        return user

    async def deactivate_user(self, user_id: UUID, actor_id: Optional[UUID] = None) -> None:
        user = await self.get_user(user_id)
        user.is_active = False
        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="delete",
            user_id=actor_id,
        )

    # ──────────────── Roles ────────────────

    async def create_role(self, data: RoleCreate, creator_id: Optional[UUID] = None) -> Role:
        result = await self.db.execute(select(Role).where(Role.name == data.name))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Papel já existe")

        role = Role(id=uuid.uuid4(), name=data.name, description=data.description)
        role.permissions = [
            Permission(
                id=uuid.uuid4(),
                role_id=role.id,
                module=p.module,
                can_create=p.can_create,
                can_read=p.can_read,
                can_update=p.can_update,
                can_delete=p.can_delete,
            )
            for p in data.permissions
        ]
        self.db.add(role)
        await self.db.flush()
        await self.audit.log(
            entity_type="role",
            entity_id=role.id,
            action="create",
            user_id=creator_id,
            new_values={"name": role.name},
        )
        return role

    async def list_roles(self):
        result = await self.db.execute(
            select(Role)
            .where(Role.is_active == True)
            .options(selectinload(Role.permissions))
        )
        return result.scalars().all()

    async def get_role(self, role_id: UUID) -> Role:
        result = await self.db.execute(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Papel não encontrado")
        return role

    async def update_role(
        self, role_id: UUID, data: RoleUpdate, updater_id: Optional[UUID] = None
    ) -> Role:
        role = await self.get_role(role_id)
        old_name = role.name

        if data.name is not None:
            role.name = data.name
        if data.description is not None:
            role.description = data.description
        if data.is_active is not None:
            role.is_active = data.is_active
        if data.permissions is not None:
            # Replace permissions
            for perm in role.permissions:
                await self.db.delete(perm)
            role.permissions = [
                Permission(
                    id=uuid.uuid4(),
                    role_id=role.id,
                    module=p.module,
                    can_create=p.can_create,
                    can_read=p.can_read,
                    can_update=p.can_update,
                    can_delete=p.can_delete,
                )
                for p in data.permissions
            ]

        await self.db.flush()
        await self.db.refresh(role)
        await self.audit.log(
            entity_type="role",
            entity_id=role.id,
            action="update",
            user_id=updater_id,
            old_values={"name": old_name},
            new_values={"name": role.name},
        )
        return role

    async def delete_role(self, role_id: UUID, actor_id: Optional[UUID] = None) -> None:
        role = await self.get_role(role_id)
        # Soft delete
        role.is_active = False
        await self.audit.log(
            entity_type="role",
            entity_id=role.id,
            action="delete",
            user_id=actor_id,
        )

    # ──────────────── Seed ────────────────

    async def seed_default_roles(self) -> None:
        """Cria papéis padrão se não existirem."""
        MODULES = ["contacts", "accounts", "opportunities", "pipeline", "reports", "admin", "audit"]

        default_roles = [
            {
                "name": RoleName.ADMIN,
                "description": "Administrador com acesso total",
                "perms": {m: (True, True, True, True) for m in MODULES},
            },
            {
                "name": RoleName.MANAGER,
                "description": "Gestor comercial",
                "perms": {
                    "contacts": (True, True, True, False),
                    "accounts": (True, True, True, False),
                    "opportunities": (True, True, True, False),
                    "pipeline": (True, True, True, False),
                    "reports": (False, True, False, False),
                    "admin": (False, True, False, False),
                    "audit": (False, True, False, False),
                },
            },
            {
                "name": RoleName.SELLER,
                "description": "Vendedor",
                "perms": {
                    "contacts": (True, True, True, False),
                    "accounts": (True, True, True, False),
                    "opportunities": (True, True, True, False),
                    "pipeline": (False, True, True, False),
                    "reports": (False, True, False, False),
                    "admin": (False, False, False, False),
                    "audit": (False, False, False, False),
                },
            },
            {
                "name": RoleName.VIEWER,
                "description": "Visualizador (somente leitura)",
                "perms": {
                    m: (False, True, False, False) for m in MODULES
                },
            },
        ]

        for role_def in default_roles:
            exists = await self.db.execute(
                select(Role).where(Role.name == role_def["name"])
            )
            if exists.scalar_one_or_none():
                continue

            role = Role(
                id=uuid.uuid4(),
                name=role_def["name"],
                description=role_def["description"],
            )
            role.permissions = [
                Permission(
                    id=uuid.uuid4(),
                    role_id=role.id,
                    module=mod,
                    can_create=perms[0],
                    can_read=perms[1],
                    can_update=perms[2],
                    can_delete=perms[3],
                )
                for mod, perms in role_def["perms"].items()
            ]
            self.db.add(role)

        await self.db.flush()
