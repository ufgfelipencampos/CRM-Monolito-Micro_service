from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Import here to avoid circular imports
    from app.modules.auth.models import User

    result = await db.execute(
        select(User)
        .where(User.id == UUID(user_id))
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user


def require_permission(module: str, action: str):
    """Factory que retorna uma dependency de verificação de permissão."""

    async def permission_checker(current_user=Depends(get_current_active_user)):
        from app.modules.auth.models import RoleName

        # Superadmin bypass
        for role in current_user.roles:
            if role.name == RoleName.ADMIN:
                return current_user

        # Verifica permissão específica
        for role in current_user.roles:
            for perm in role.permissions:
                if perm.module == module:
                    allowed = getattr(perm, f"can_{action}", False)
                    if allowed:
                        return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permissão negada: {module}:{action}",
        )

    return permission_checker


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


CurrentUser = Annotated[object, Depends(get_current_active_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
