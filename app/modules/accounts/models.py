import uuid
from typing import Optional, List

from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.base_model import TimestampMixin, UUIDMixin, AuditUserMixin
from app.modules.contacts.models import contact_accounts


class Account(Base, UUIDMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cnpj: Mapped[Optional[str]] = mapped_column(
        String(18), unique=True, nullable=True, index=True
    )
    segment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # pequena | media | grande | enterprise
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Self-referential hierarchy (matriz/filiais)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    parent: Mapped[Optional["Account"]] = relationship(
        "Account", remote_side="Account.id", back_populates="children"
    )
    children: Mapped[List["Account"]] = relationship("Account", back_populates="parent")

    contacts: Mapped[List["Contact"]] = relationship(  # noqa: F821
        "Contact", secondary=contact_accounts, back_populates="accounts"
    )
