from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.opportunities.models import Opportunity, PipelineStage, OpportunityStatus
from app.modules.opportunities.schemas import (
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityClose,
    OpportunityMoveStage,
    PipelineStageCreate,
    PipelineStageUpdate,
    OpportunityFilters,
)
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginationParams


class OpportunityService:
    def __init__(self, db: AsyncSession, audit: AuditService):
        self.db = db
        self.audit = audit

    # ──────────────── Pipeline Stages ────────────────

    async def create_stage(
        self, data: PipelineStageCreate, creator_id: Optional[UUID] = None
    ) -> PipelineStage:
        stage = PipelineStage(
            id=uuid.uuid4(),
            name=data.name,
            order=data.order,
            probability=data.probability,
        )
        self.db.add(stage)
        await self.db.flush()
        await self.audit.log(
            entity_type="pipeline_stage",
            entity_id=stage.id,
            action="create",
            user_id=creator_id,
            new_values={"name": stage.name, "order": stage.order},
        )
        return stage

    async def list_stages(self) -> list[PipelineStage]:
        result = await self.db.execute(
            select(PipelineStage)
            .where(PipelineStage.is_active == True)
            .order_by(PipelineStage.order)
        )
        return result.scalars().all()

    async def get_stage(self, stage_id: UUID) -> PipelineStage:
        result = await self.db.execute(
            select(PipelineStage).where(PipelineStage.id == stage_id)
        )
        stage = result.scalar_one_or_none()
        if not stage:
            raise HTTPException(status_code=404, detail="Estágio não encontrado")
        return stage

    async def update_stage(
        self, stage_id: UUID, data: PipelineStageUpdate, updater_id: Optional[UUID] = None
    ) -> PipelineStage:
        stage = await self.get_stage(stage_id)
        if data.name is not None:
            stage.name = data.name
        if data.order is not None:
            stage.order = data.order
        if data.probability is not None:
            stage.probability = data.probability
        if data.is_active is not None:
            # Cannot deactivate stage with active opportunities
            if not data.is_active:
                count = (
                    await self.db.execute(
                        select(func.count()).where(
                            Opportunity.stage_id == stage_id,
                            Opportunity.status == OpportunityStatus.ACTIVE,
                        )
                    )
                ).scalar_one()
                if count > 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Estágio possui {count} oportunidades ativas. Mova-as primeiro.",
                    )
            stage.is_active = data.is_active
        await self.db.flush()
        await self.audit.log(
            entity_type="pipeline_stage",
            entity_id=stage.id,
            action="update",
            user_id=updater_id,
        )
        return stage

    # ──────────────── Opportunities ────────────────

    async def create(
        self, data: OpportunityCreate, creator_id: Optional[UUID] = None
    ) -> Opportunity:
        stage = await self.get_stage(data.stage_id)

        # Validate contact and account exist
        from app.modules.contacts.models import Contact
        from app.modules.accounts.models import Account

        contact = (
            await self.db.execute(
                select(Contact).where(Contact.id == data.contact_id, Contact.is_active == True)
            )
        ).scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contato não encontrado ou inativo")

        account = (
            await self.db.execute(
                select(Account).where(Account.id == data.account_id, Account.is_active == True)
            )
        ).scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Conta não encontrada ou inativa")

        # Auto-set probability from stage if not provided
        probability = data.probability if data.probability is not None else stage.probability

        opp = Opportunity(
            id=uuid.uuid4(),
            title=data.title,
            contact_id=data.contact_id,
            account_id=data.account_id,
            value=data.value,
            close_date=data.close_date,
            probability=probability,
            stage_id=data.stage_id,
            source=data.source,
            notes=data.notes,
            owner_id=data.owner_id,
            status=OpportunityStatus.ACTIVE,
            created_by=creator_id,
            updated_by=creator_id,
        )
        self.db.add(opp)
        await self.db.flush()
        await self.audit.log(
            entity_type="opportunity",
            entity_id=opp.id,
            action="create",
            user_id=creator_id,
            new_values={"title": opp.title, "value": str(opp.value)},
        )
        await self.db.refresh(opp, ["stage", "contact", "account"])
        return opp

    async def get(self, opp_id: UUID) -> Opportunity:
        result = await self.db.execute(
            select(Opportunity)
            .where(Opportunity.id == opp_id)
            .options(
                selectinload(Opportunity.stage),
                selectinload(Opportunity.contact),
                selectinload(Opportunity.account),
            )
        )
        opp = result.scalar_one_or_none()
        if not opp:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
        return opp

    async def list(self, filters: OpportunityFilters, pagination: PaginationParams):
        q = select(Opportunity).options(
            selectinload(Opportunity.stage),
            selectinload(Opportunity.contact),
            selectinload(Opportunity.account),
        )
        if filters.title:
            q = q.where(Opportunity.title.ilike(f"%{filters.title}%"))
        if filters.stage_id:
            q = q.where(Opportunity.stage_id == filters.stage_id)
        if filters.status:
            q = q.where(Opportunity.status == filters.status)
        if filters.owner_id:
            q = q.where(Opportunity.owner_id == filters.owner_id)
        if filters.contact_id:
            q = q.where(Opportunity.contact_id == filters.contact_id)
        if filters.account_id:
            q = q.where(Opportunity.account_id == filters.account_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(Opportunity.created_at.desc()).offset(pagination.offset).limit(
            pagination.per_page
        )
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update(
        self, opp_id: UUID, data: OpportunityUpdate, updater_id: Optional[UUID] = None
    ) -> Opportunity:
        opp = await self.get(opp_id)
        if opp.status != OpportunityStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Oportunidade já encerrada")

        old = {"title": opp.title, "value": str(opp.value), "stage_id": str(opp.stage_id)}

        if data.title is not None:
            opp.title = data.title
        if data.contact_id is not None:
            opp.contact_id = data.contact_id
        if data.account_id is not None:
            opp.account_id = data.account_id
        if data.value is not None:
            opp.value = data.value
        if data.close_date is not None:
            opp.close_date = data.close_date
        if data.probability is not None:
            opp.probability = data.probability
        if data.stage_id is not None:
            await self.get_stage(data.stage_id)  # validate
            opp.stage_id = data.stage_id
        if data.source is not None:
            opp.source = data.source
        if data.notes is not None:
            opp.notes = data.notes
        if data.owner_id is not None:
            opp.owner_id = data.owner_id

        opp.updated_by = updater_id
        await self.db.flush()
        await self.db.refresh(opp)
        await self.audit.log(
            entity_type="opportunity",
            entity_id=opp.id,
            action="update",
            user_id=updater_id,
            old_values=old,
            new_values={"title": opp.title, "stage_id": str(opp.stage_id)},
        )
        return opp

    async def move_stage(
        self, opp_id: UUID, data: OpportunityMoveStage, updater_id: Optional[UUID] = None
    ) -> Opportunity:
        opp = await self.get(opp_id)
        if opp.status != OpportunityStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Oportunidade já encerrada")
        stage = await self.get_stage(data.stage_id)
        old_stage_id = opp.stage_id
        opp.stage_id = stage.id
        # Auto-update probability from stage
        opp.probability = stage.probability
        opp.updated_by = updater_id
        await self.db.flush()
        await self.audit.log(
            entity_type="opportunity",
            entity_id=opp.id,
            action="move_stage",
            user_id=updater_id,
            old_values={"stage_id": str(old_stage_id)},
            new_values={"stage_id": str(stage.id), "stage_name": stage.name},
        )
        await self.db.refresh(opp, ["stage"])
        return opp

    async def close(
        self, opp_id: UUID, data: OpportunityClose, actor_id: Optional[UUID] = None
    ) -> Opportunity:
        opp = await self.get(opp_id)
        if opp.status != OpportunityStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Oportunidade já encerrada")

        if data.status == OpportunityStatus.LOST and not data.lost_reason:
            raise HTTPException(
                status_code=400, detail="Motivo de perda obrigatório ao marcar como perdida"
            )

        old_status = opp.status
        opp.status = data.status
        opp.lost_reason = data.lost_reason
        opp.closed_at = datetime.now(timezone.utc)
        opp.closed_by = actor_id
        opp.updated_by = actor_id
        await self.db.flush()

        await self.audit.log(
            entity_type="opportunity",
            entity_id=opp.id,
            action="close",
            user_id=actor_id,
            old_values={"status": old_status},
            new_values={
                "status": opp.status,
                "lost_reason": opp.lost_reason,
                "closed_at": opp.closed_at.isoformat() if opp.closed_at else None,
            },
        )
        return opp

    async def get_pipeline_view(
        self,
        owner_id: Optional[UUID] = None,
    ) -> list[dict]:
        """Retorna oportunidades ativas agrupadas por estágio."""
        stages = await self.list_stages()
        pipeline = []

        for stage in stages:
            q = select(Opportunity).where(
                Opportunity.stage_id == stage.id,
                Opportunity.status == OpportunityStatus.ACTIVE,
            ).options(
                selectinload(Opportunity.contact),
                selectinload(Opportunity.account),
                selectinload(Opportunity.stage),
            )
            if owner_id:
                q = q.where(Opportunity.owner_id == owner_id)

            result = await self.db.execute(q)
            opps = result.scalars().all()

            total_value = sum(o.value or Decimal("0") for o in opps)
            pipeline.append(
                {
                    "stage": stage,
                    "opportunities": opps,
                    "total_value": total_value,
                    "count": len(opps),
                }
            )

        return pipeline
