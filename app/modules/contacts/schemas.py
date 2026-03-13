from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    cargo: Optional[str] = None
    lead_source: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    owner_id: Optional[UUID] = None
    account_ids: Optional[list[UUID]] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    cargo: Optional[str] = None
    lead_source: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    owner_id: Optional[UUID] = None
    account_ids: Optional[list[UUID]] = None


class AccountSummary(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ContactResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: Optional[str]
    cargo: Optional[str]
    lead_source: Optional[str]
    tags: Optional[list[str]]
    notes: Optional[str]
    is_active: bool
    owner_id: Optional[UUID]
    accounts: list[AccountSummary]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    updated_by: Optional[UUID]

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: Optional[str]
    cargo: Optional[str]
    lead_source: Optional[str]
    tags: Optional[list[str]]
    is_active: bool
    owner_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactFilters(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    lead_source: Optional[str] = None
    is_active: Optional[bool] = True
    owner_id: Optional[UUID] = None
    tag: Optional[str] = None
