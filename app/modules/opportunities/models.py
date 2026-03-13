import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, Boolean, ForeignKey, Numeric, Integer, Text, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.base_model import TimestampMixin, UUIDMixin, AuditUserMixin


class OpportunityStatus(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"


class PipelineStage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pipeline_stages"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    probability: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity", back_populates="stage"
    )


class Opportunity(Base, UUIDMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "opportunities"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    probability: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=OpportunityStatus.ACTIVE, nullable=False, index=True
    )
    lost_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    stage: Mapped["PipelineStage"] = relationship("PipelineStage", back_populates="opportunities")
    contact: Mapped["Contact"] = relationship("Contact")  # noqa: F821
    account: Mapped["Account"] = relationship("Account")  # noqa: F821
