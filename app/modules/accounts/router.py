from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_permission
from app.modules.audit.service import AuditService
from app.modules.accounts.schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
    AccountFilters,
)
from app.modules.accounts.service import AccountService
from app.shared.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/accounts", tags=["Contas (Empresas)"])


def _svc(db: AsyncSession) -> AccountService:
    return AccountService(db, AuditService(db))


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("accounts", "create"))],
)
async def create_account(
    data: AccountCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create(data, creator_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[AccountListResponse],
    dependencies=[Depends(require_permission("accounts", "read"))],
)
async def list_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    name: str | None = None,
    cnpj: str | None = None,
    segment: str | None = None,
    is_active: bool | None = True,
    owner_id: UUID | None = None,
):
    svc = _svc(db)
    filters = AccountFilters(
        name=name, cnpj=cnpj, segment=segment, is_active=is_active, owner_id=owner_id
    )
    items, total = await svc.list(filters, PaginationParams(page=page, per_page=per_page))
    return PaginatedResponse.build(items, total, page, per_page)


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    dependencies=[Depends(require_permission("accounts", "read"))],
)
async def get_account(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get(account_id)


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    dependencies=[Depends(require_permission("accounts", "update"))],
)
async def update_account(
    account_id: UUID,
    data: AccountUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update(account_id, data, updater_id=current_user.id)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("accounts", "delete"))],
)
async def deactivate_account(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    await _svc(db).deactivate(account_id, actor_id=current_user.id)


@router.get(
    "/{account_id}/hierarchy",
    dependencies=[Depends(require_permission("accounts", "read"))],
)
async def get_account_hierarchy(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get_hierarchy(account_id)
