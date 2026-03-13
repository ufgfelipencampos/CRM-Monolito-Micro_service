from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_permission
from app.modules.audit.service import AuditService
from app.modules.opportunities.models import OpportunityStatus
from app.modules.opportunities.schemas import (
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityResponse,
    OpportunityListResponse,
    OpportunityClose,
    OpportunityMoveStage,
    OpportunityFilters,
    PipelineStageCreate,
    PipelineStageUpdate,
    PipelineStageResponse,
    PipelineView,
    PipelineColumn,
)
from app.modules.opportunities.service import OpportunityService
from app.shared.pagination import PaginationParams, PaginatedResponse

router = APIRouter(tags=["Oportunidades & Pipeline"])


def _svc(db: AsyncSession) -> OpportunityService:
    return OpportunityService(db, AuditService(db))


# ──────────────── Pipeline Stages ────────────────

@router.post(
    "/pipeline/stages",
    response_model=PipelineStageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin", "create"))],
)
async def create_stage(
    data: PipelineStageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create_stage(data, creator_id=current_user.id)


@router.get(
    "/pipeline/stages",
    response_model=list[PipelineStageResponse],
    dependencies=[Depends(require_permission("pipeline", "read"))],
)
async def list_stages(db: Annotated[AsyncSession, Depends(get_db)]):
    return await _svc(db).list_stages()


@router.put(
    "/pipeline/stages/{stage_id}",
    response_model=PipelineStageResponse,
    dependencies=[Depends(require_permission("admin", "update"))],
)
async def update_stage(
    stage_id: UUID,
    data: PipelineStageUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update_stage(stage_id, data, updater_id=current_user.id)


# ──────────────── Pipeline View ────────────────

@router.get(
    "/pipeline",
    response_model=PipelineView,
    dependencies=[Depends(require_permission("pipeline", "read"))],
)
async def get_pipeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner_id: UUID | None = None,
):
    svc = _svc(db)
    columns_data = await svc.get_pipeline_view(owner_id=owner_id)
    columns = [
        PipelineColumn(
            stage=PipelineStageResponse.model_validate(col["stage"]),
            opportunities=[
                OpportunityListResponse.model_validate(o) for o in col["opportunities"]
            ],
            total_value=col["total_value"],
            count=col["count"],
        )
        for col in columns_data
    ]
    return PipelineView(columns=columns)


# ──────────────── Opportunities ────────────────

@router.post(
    "/opportunities",
    response_model=OpportunityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("opportunities", "create"))],
)
async def create_opportunity(
    data: OpportunityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create(data, creator_id=current_user.id)


@router.get(
    "/opportunities",
    response_model=PaginatedResponse[OpportunityListResponse],
    dependencies=[Depends(require_permission("opportunities", "read"))],
)
async def list_opportunities(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    title: str | None = None,
    stage_id: UUID | None = None,
    status: OpportunityStatus | None = None,
    owner_id: UUID | None = None,
    contact_id: UUID | None = None,
    account_id: UUID | None = None,
):
    svc = _svc(db)
    filters = OpportunityFilters(
        title=title,
        stage_id=stage_id,
        status=status,
        owner_id=owner_id,
        contact_id=contact_id,
        account_id=account_id,
    )
    items, total = await svc.list(filters, PaginationParams(page=page, per_page=per_page))
    return PaginatedResponse.build(items, total, page, per_page)


@router.get(
    "/opportunities/{opp_id}",
    response_model=OpportunityResponse,
    dependencies=[Depends(require_permission("opportunities", "read"))],
)
async def get_opportunity(
    opp_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get(opp_id)


@router.put(
    "/opportunities/{opp_id}",
    response_model=OpportunityResponse,
    dependencies=[Depends(require_permission("opportunities", "update"))],
)
async def update_opportunity(
    opp_id: UUID,
    data: OpportunityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update(opp_id, data, updater_id=current_user.id)


@router.patch(
    "/opportunities/{opp_id}/stage",
    response_model=OpportunityResponse,
    dependencies=[Depends(require_permission("opportunities", "update"))],
)
async def move_opportunity_stage(
    opp_id: UUID,
    data: OpportunityMoveStage,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).move_stage(opp_id, data, updater_id=current_user.id)


@router.patch(
    "/opportunities/{opp_id}/close",
    response_model=OpportunityResponse,
    dependencies=[Depends(require_permission("opportunities", "update"))],
)
async def close_opportunity(
    opp_id: UUID,
    data: OpportunityClose,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).close(opp_id, data, actor_id=current_user.id)
