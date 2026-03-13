from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_permission
from app.core.security import decode_token
from app.modules.audit.service import AuditService
from app.modules.auth.schemas import (
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    UserCreate,
    UserUpdate,
    UserResponse,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserMeResponse,
)
from app.modules.auth.service import AuthService
from app.shared.pagination import PaginationParams, PaginatedResponse

router = APIRouter()


def _get_services(db: AsyncSession) -> tuple[AuthService, AuditService]:
    audit = AuditService(db)
    auth = AuthService(db, audit)
    return auth, audit


# ──────────────── Auth endpoints ────────────────

@router.post("/auth/login", response_model=TokenResponse, tags=["Autenticação"])
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.modules.auth.schemas import LoginRequest
    from app.core.dependencies import get_client_ip
    auth, _ = _get_services(db)
    return await auth.login(
        LoginRequest(email=form_data.username, password=form_data.password),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


@router.post("/auth/refresh", response_model=TokenResponse, tags=["Autenticação"])
async def refresh_token(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    auth, _ = _get_services(db)
    return await auth.refresh_token(data.refresh_token)


@router.post("/auth/forgot-password", tags=["Autenticação"])
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    auth, _ = _get_services(db)
    # NOTE: In production the token is sent via email; for dev it's returned in the response
    token = await auth.forgot_password(data.email)
    return {"message": "Se o e-mail existir, um link de recuperação foi enviado", "dev_token": token}


@router.post("/auth/reset-password", status_code=status.HTTP_204_NO_CONTENT, tags=["Autenticação"])
async def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    auth, _ = _get_services(db)
    await auth.reset_password(data.token, data.new_password)


@router.get("/auth/me", response_model=UserMeResponse, tags=["Autenticação"])
async def get_me(current_user=Depends(get_current_active_user)):
    return UserMeResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=[r.name for r in current_user.roles],
    )


@router.post(
    "/auth/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Autenticação"],
)
async def change_password(
    data: ChangePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    from app.core.security import verify_password, hash_password
    from fastapi import HTTPException

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.password_hash = hash_password(data.new_password)
    audit = AuditService(db)
    await audit.log(
        entity_type="user",
        entity_id=current_user.id,
        action="password_change",
        user_id=current_user.id,
    )


# ──────────────── Admin - Users ────────────────

@router.post(
    "/admin/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Administração - Usuários"],
    dependencies=[Depends(require_permission("admin", "create"))],
)
async def create_user(
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    auth, _ = _get_services(db)
    return await auth.create_user(data, creator_id=current_user.id)


@router.get(
    "/admin/users",
    response_model=PaginatedResponse[UserResponse],
    tags=["Administração - Usuários"],
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    per_page: int = 20,
):
    auth, _ = _get_services(db)
    users, total = await auth.list_users(page=page, per_page=per_page)
    return PaginatedResponse.build(users, total, page, per_page)


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["Administração - Usuários"],
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def get_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from uuid import UUID
    auth, _ = _get_services(db)
    return await auth.get_user(UUID(user_id))


@router.put(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["Administração - Usuários"],
    dependencies=[Depends(require_permission("admin", "update"))],
)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    from uuid import UUID
    auth, _ = _get_services(db)
    return await auth.update_user(UUID(user_id), data, updater_id=current_user.id)


@router.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Administração - Usuários"],
    dependencies=[Depends(require_permission("admin", "delete"))],
)
async def deactivate_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    from uuid import UUID
    auth, _ = _get_services(db)
    await auth.deactivate_user(UUID(user_id), actor_id=current_user.id)


# ──────────────── Admin - Roles ────────────────

@router.post(
    "/admin/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Administração - Papéis"],
    dependencies=[Depends(require_permission("admin", "create"))],
)
async def create_role(
    data: RoleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    auth, _ = _get_services(db)
    return await auth.create_role(data, creator_id=current_user.id)


@router.get(
    "/admin/roles",
    response_model=list[RoleResponse],
    tags=["Administração - Papéis"],
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def list_roles(db: Annotated[AsyncSession, Depends(get_db)]):
    auth, _ = _get_services(db)
    return await auth.list_roles()


@router.get(
    "/admin/roles/{role_id}",
    response_model=RoleResponse,
    tags=["Administração - Papéis"],
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def get_role(role_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    from uuid import UUID
    auth, _ = _get_services(db)
    return await auth.get_role(UUID(role_id))


@router.put(
    "/admin/roles/{role_id}",
    response_model=RoleResponse,
    tags=["Administração - Papéis"],
    dependencies=[Depends(require_permission("admin", "update"))],
)
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    from uuid import UUID
    auth, _ = _get_services(db)
    return await auth.update_role(UUID(role_id), data, updater_id=current_user.id)


@router.delete(
    "/admin/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Administração - Papéis"],
    dependencies=[Depends(require_permission("admin", "delete"))],
)
async def delete_role(
    role_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    from uuid import UUID
    auth, _ = _get_services(db)
    await auth.delete_role(UUID(role_id), actor_id=current_user.id)
