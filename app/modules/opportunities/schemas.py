from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from app.modules.opportunities.models import OpportunityStatus


# ──────────────── Pipeline Stages ────────────────

class PipelineStageCreate(BaseModel):
    name: str
    order: int
    probability: Decimal = Decimal("0.00")

    @field_validator("probability")
    @classmethod
    def validate_probability(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 100:
            raise ValueError("Probabilidade deve estar entre 0 e 100")
        return v


class PipelineStageUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    probability: Optional[Decimal] = None
    is_active: Optional[bool] = None


class PipelineStageResponse(BaseModel):
    id: UUID
    name: str
    order: int
    probability: Decimal
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────── Opportunities ────────────────

class OpportunityCreate(BaseModel):
    title: str
    contact_id: UUID
    account_id: UUID
    value: Optional[Decimal] = None
    close_date: Optional[date] = None
    probability: Optional[Decimal] = None
    stage_id: UUID
    source: Optional[str] = None
    notes: Optional[str] = None
    owner_id: Optional[UUID] = None

    @field_validator("probability")
    @classmethod
    def validate_probability(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Probabilidade deve estar entre 0 e 100")
        return v


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    value: Optional[Decimal] = None
    close_date: Optional[date] = None
    probability: Optional[Decimal] = None
    stage_id: Optional[UUID] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    owner_id: Optional[UUID] = None


class OpportunityMoveStage(BaseModel):
    stage_id: UUID


class OpportunityClose(BaseModel):
    status: OpportunityStatus
    lost_reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_final_status(cls, v: OpportunityStatus) -> OpportunityStatus:
        if v == OpportunityStatus.ACTIVE:
            raise ValueError("Status deve ser 'won' ou 'lost'")
        return v

    @model_validator(mode="after")
    def validate_lost_reason(self) -> "OpportunityClose":
        if self.status == OpportunityStatus.LOST and not self.lost_reason:
            raise ValueError("Motivo de perda obrigatório ao marcar como perdida")
        return self


class StageSummary(BaseModel):
    id: UUID
    name: str
    order: int
    probability: Decimal

    model_config = {"from_attributes": True}


class ContactSummary(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class OpportunityResponse(BaseModel):
    id: UUID
    title: str
    contact_id: UUID
    account_id: UUID
    value: Optional[Decimal]
    close_date: Optional[date]
    probability: Optional[Decimal]
    stage_id: UUID
    source: Optional[str]
    status: str
    lost_reason: Optional[str]
    notes: Optional[str]
    owner_id: Optional[UUID]
    closed_at: Optional[datetime]
    closed_by: Optional[UUID]
    stage: StageSummary
    contact: ContactSummary
    account: AccountSummary
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]

    model_config = {"from_attributes": True}


class OpportunityListResponse(BaseModel):
    id: UUID
    title: str
    contact_id: UUID
    account_id: UUID
    value: Optional[Decimal]
    close_date: Optional[date]
    probability: Optional[Decimal]
    stage_id: UUID
    status: str
    owner_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineColumn(BaseModel):
    stage: PipelineStageResponse
    opportunities: List[OpportunityListResponse]
    total_value: Decimal
    count: int


class PipelineView(BaseModel):
    columns: List[PipelineColumn]


class OpportunityFilters(BaseModel):
    title: Optional[str] = None
    stage_id: Optional[UUID] = None
    status: Optional[OpportunityStatus] = None
    owner_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
