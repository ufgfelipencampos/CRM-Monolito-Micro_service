from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_permission
from app.modules.audit.service import AuditService
from app.modules.contacts.schemas import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactListResponse,
    ContactFilters,
)
from app.modules.contacts.service import ContactService
from app.shared.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/contacts", tags=["Contatos"])


def _svc(db: AsyncSession) -> ContactService:
    return ContactService(db, AuditService(db))


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("contacts", "create"))],
)
async def create_contact(
    data: ContactCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create(data, creator_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[ContactListResponse],
    dependencies=[Depends(require_permission("contacts", "read"))],
)
async def list_contacts(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    name: str | None = None,
    email: str | None = None,
    lead_source: str | None = None,
    is_active: bool | None = True,
    owner_id: UUID | None = None,
    tag: str | None = None,
):
    svc = _svc(db)
    filters = ContactFilters(
        name=name,
        email=email,
        lead_source=lead_source,
        is_active=is_active,
        owner_id=owner_id,
        tag=tag,
    )
    items, total = await svc.list(filters, PaginationParams(page=page, per_page=per_page))
    return PaginatedResponse.build(items, total, page, per_page)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contacts", "read"))],
)
async def get_contact(
    contact_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get(contact_id)


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contacts", "update"))],
)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update(contact_id, data, updater_id=current_user.id)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("contacts", "delete"))],
)
async def deactivate_contact(
    contact_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    await _svc(db).deactivate(contact_id, actor_id=current_user.id)
