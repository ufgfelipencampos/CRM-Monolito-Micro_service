import uuid
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.accounts.models import Account
from app.modules.accounts.schemas import AccountCreate, AccountUpdate, AccountFilters
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginationParams


class AccountService:
    def __init__(self, db: AsyncSession, audit: AuditService):
        self.db = db
        self.audit = audit

    async def create(self, data: AccountCreate, creator_id: Optional[UUID] = None) -> Account:
        if data.cnpj:
            exists = await self.db.execute(
                select(Account).where(Account.cnpj == data.cnpj)
            )
            if exists.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="CNPJ já cadastrado")

        if data.parent_id:
            await self._validate_no_cycle(data.parent_id, None)

        address_dict = data.address.model_dump() if data.address else None

        account = Account(
            id=uuid.uuid4(),
            name=data.name,
            cnpj=data.cnpj,
            segment=data.segment,
            size=data.size,
            address=address_dict,
            website=data.website,
            notes=data.notes,
            parent_id=data.parent_id,
            owner_id=data.owner_id,
            created_by=creator_id,
            updated_by=creator_id,
        )

        if data.contact_ids:
            from app.modules.contacts.models import Contact
            contacts_result = await self.db.execute(
                select(Contact).where(
                    Contact.id.in_(data.contact_ids), Contact.is_active == True
                )
            )
            account.contacts = list(contacts_result.scalars().all())

        self.db.add(account)
        await self.db.flush()

        await self.audit.log(
            entity_type="account",
            entity_id=account.id,
            action="create",
            user_id=creator_id,
            new_values={"name": account.name, "cnpj": account.cnpj},
        )
        await self.db.refresh(account, ["contacts", "children"])
        return account

    async def get(self, account_id: UUID) -> Account:
        result = await self.db.execute(
            select(Account)
            .where(Account.id == account_id)
            .options(
                selectinload(Account.contacts),
                selectinload(Account.children),
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Conta não encontrada")
        return account

    async def list(self, filters: AccountFilters, pagination: PaginationParams):
        q = select(Account).where(
            Account.is_active == (filters.is_active if filters.is_active is not None else True)
        )
        if filters.name:
            q = q.where(Account.name.ilike(f"%{filters.name}%"))
        if filters.cnpj:
            q = q.where(Account.cnpj.ilike(f"%{filters.cnpj}%"))
        if filters.segment:
            q = q.where(Account.segment == filters.segment)
        if filters.owner_id:
            q = q.where(Account.owner_id == filters.owner_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(Account.name).offset(pagination.offset).limit(pagination.per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update(
        self,
        account_id: UUID,
        data: AccountUpdate,
        updater_id: Optional[UUID] = None,
    ) -> Account:
        account = await self.get(account_id)
        old = {"name": account.name, "cnpj": account.cnpj}

        if data.cnpj and data.cnpj != account.cnpj:
            exists = await self.db.execute(
                select(Account).where(Account.cnpj == data.cnpj, Account.id != account_id)
            )
            if exists.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="CNPJ já cadastrado")

        if data.parent_id and data.parent_id != account.parent_id:
            await self._validate_no_cycle(data.parent_id, account_id)

        if data.name is not None:
            account.name = data.name
        if data.cnpj is not None:
            account.cnpj = data.cnpj
        if data.segment is not None:
            account.segment = data.segment
        if data.size is not None:
            account.size = data.size
        if data.address is not None:
            account.address = data.address.model_dump()
        if data.website is not None:
            account.website = data.website
        if data.notes is not None:
            account.notes = data.notes
        if data.parent_id is not None:
            account.parent_id = data.parent_id
        if data.owner_id is not None:
            account.owner_id = data.owner_id
        if data.contact_ids is not None:
            from app.modules.contacts.models import Contact
            contacts_result = await self.db.execute(
                select(Contact).where(
                    Contact.id.in_(data.contact_ids), Contact.is_active == True
                )
            )
            account.contacts = list(contacts_result.scalars().all())

        account.updated_by = updater_id
        await self.db.flush()
        await self.db.refresh(account)

        await self.audit.log(
            entity_type="account",
            entity_id=account.id,
            action="update",
            user_id=updater_id,
            old_values=old,
            new_values={"name": account.name, "cnpj": account.cnpj},
        )
        return account

    async def deactivate(self, account_id: UUID, actor_id: Optional[UUID] = None) -> None:
        account = await self.get(account_id)
        if not account.is_active:
            raise HTTPException(status_code=400, detail="Conta já inativa")
        account.is_active = False
        account.updated_by = actor_id
        await self.db.flush()
        await self.audit.log(
            entity_type="account",
            entity_id=account.id,
            action="delete",
            user_id=actor_id,
        )

    async def get_hierarchy(self, account_id: UUID) -> dict:
        account = await self.get(account_id)
        return await self._build_tree(account)

    async def _build_tree(self, account: Account) -> dict:
        result = await self.db.execute(
            select(Account)
            .where(Account.parent_id == account.id, Account.is_active == True)
            .options(selectinload(Account.children))
        )
        children = result.scalars().all()
        return {
            "id": str(account.id),
            "name": account.name,
            "children": [await self._build_tree(c) for c in children],
        }

    async def _validate_no_cycle(self, parent_id: UUID, account_id: Optional[UUID]) -> None:
        """Garante que não há ciclo na hierarquia."""
        visited = set()
        current_id = parent_id
        while current_id:
            if account_id and current_id == account_id:
                raise HTTPException(status_code=400, detail="Hierarquia circular detectada")
            if current_id in visited:
                raise HTTPException(status_code=400, detail="Hierarquia circular detectada")
            visited.add(current_id)
            result = await self.db.execute(
                select(Account.parent_id).where(Account.id == current_id)
            )
            row = result.scalar_one_or_none()
            current_id = row
