from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.audit.schemas import AuditLogResponse, AuditFilters
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/audit", tags=["Auditoria"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogResponse],
    dependencies=[Depends(require_permission("audit", "read"))],
)
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    action: str | None = None,
    user_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
):
    svc = AuditService(db)
    filters = AuditFilters(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
    )
    items, total = await svc.query(filters, PaginationParams(page=page, per_page=per_page))
    return PaginatedResponse.build(items, total, page, per_page)
