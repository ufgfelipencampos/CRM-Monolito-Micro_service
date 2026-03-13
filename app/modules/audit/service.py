import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditFilters
from app.shared.pagination import PaginationParams


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        entity_type: str,
        entity_id: UUID,
        action: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ) -> AuditLog:
        entry = AuditLog(
            id=uuid.uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            old_values=old_values,
            new_values=new_values,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def query(
        self,
        filters: AuditFilters,
        pagination: PaginationParams,
    ):
        q = select(AuditLog)
        if filters.entity_type:
            q = q.where(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id:
            q = q.where(AuditLog.entity_id == filters.entity_id)
        if filters.action:
            q = q.where(AuditLog.action == filters.action)
        if filters.user_id:
            q = q.where(AuditLog.user_id == filters.user_id)
        if filters.from_date:
            q = q.where(AuditLog.created_at >= filters.from_date)
        if filters.to_date:
            q = q.where(AuditLog.created_at <= filters.to_date)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(AuditLog.created_at.desc())
        q = q.offset(pagination.offset).limit(pagination.per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total
