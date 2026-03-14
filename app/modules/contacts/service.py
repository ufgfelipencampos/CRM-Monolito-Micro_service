import uuid
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.contacts.models import Contact
from app.modules.contacts.schemas import ContactCreate, ContactUpdate, ContactFilters
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginationParams


class ContactService:
    def __init__(self, db: AsyncSession, audit: AuditService):
        self.db = db
        self.audit = audit

    async def create(self, data: ContactCreate, creator_id: Optional[UUID] = None) -> Contact:
        contact = Contact(
            id=uuid.uuid4(),
            name=data.name,
            email=data.email.lower(),
            phone=data.phone,
            cargo=data.cargo,
            lead_source=data.lead_source,
            tags=data.tags,
            notes=data.notes,
            owner_id=data.owner_id,
            created_by=creator_id,
            updated_by=creator_id,
        )

        if data.account_ids:
            from app.modules.accounts.models import Account
            acc_result = await self.db.execute(
                select(Account).where(Account.id.in_(data.account_ids), Account.is_active == True)
            )
            contact.accounts = list(acc_result.scalars().all())

        self.db.add(contact)
        await self.db.flush()

        await self.audit.log(
            entity_type="contact",
            entity_id=contact.id,
            action="create",
            user_id=creator_id,
            new_values={"name": contact.name, "email": contact.email},
        )
        await self.db.refresh(contact, ["accounts"])
        return contact

    async def get(self, contact_id: UUID) -> Contact:
        result = await self.db.execute(
            select(Contact)
            .where(Contact.id == contact_id)
            .options(selectinload(Contact.accounts))
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contato não encontrado")
        return contact

    async def list(self, filters: ContactFilters, pagination: PaginationParams):
        q = (
            select(Contact)
            .where(Contact.is_active == (filters.is_active if filters.is_active is not None else True))
            .options(selectinload(Contact.accounts))
        )
        if filters.name:
            q = q.where(Contact.name.ilike(f"%{filters.name}%"))
        if filters.email:
            q = q.where(Contact.email.ilike(f"%{filters.email}%"))
        if filters.lead_source:
            q = q.where(Contact.lead_source == filters.lead_source)
        if filters.owner_id:
            q = q.where(Contact.owner_id == filters.owner_id)
        if filters.tag:
            q = q.where(Contact.tags.contains([filters.tag]))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(Contact.name).offset(pagination.offset).limit(pagination.per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update(
        self,
        contact_id: UUID,
        data: ContactUpdate,
        updater_id: Optional[UUID] = None,
    ) -> Contact:
        contact = await self.get(contact_id)
        old = {"name": contact.name, "email": contact.email}

        if data.name is not None:
            contact.name = data.name
        if data.email is not None:
            contact.email = data.email.lower()
        if data.phone is not None:
            contact.phone = data.phone
        if data.cargo is not None:
            contact.cargo = data.cargo
        if data.lead_source is not None:
            contact.lead_source = data.lead_source
        if data.tags is not None:
            contact.tags = data.tags
        if data.notes is not None:
            contact.notes = data.notes
        if data.owner_id is not None:
            contact.owner_id = data.owner_id
        if data.account_ids is not None:
            from app.modules.accounts.models import Account
            acc_result = await self.db.execute(
                select(Account).where(
                    Account.id.in_(data.account_ids), Account.is_active == True
                )
            )
            contact.accounts = list(acc_result.scalars().all())

        contact.updated_by = updater_id
        await self.db.flush()
        await self.db.refresh(contact)

        await self.audit.log(
            entity_type="contact",
            entity_id=contact.id,
            action="update",
            user_id=updater_id,
            old_values=old,
            new_values={"name": contact.name, "email": contact.email},
        )
        return contact

    async def deactivate(self, contact_id: UUID, actor_id: Optional[UUID] = None) -> None:
        contact = await self.get(contact_id)
        if not contact.is_active:
            raise HTTPException(status_code=400, detail="Contato já inativo")
        contact.is_active = False
        contact.updated_by = actor_id
        await self.db.flush()
        await self.audit.log(
            entity_type="contact",
            entity_id=contact.id,
            action="delete",
            user_id=actor_id,
        )
