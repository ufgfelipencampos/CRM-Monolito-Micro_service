from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel


class AddressSchema(BaseModel):
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = "Brasil"


class AccountCreate(BaseModel):
    name: str
    cnpj: Optional[str] = None
    segment: Optional[str] = None
    size: Optional[str] = None  # pequena | media | grande | enterprise
    address: Optional[AddressSchema] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    parent_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    contact_ids: Optional[list[UUID]] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    segment: Optional[str] = None
    size: Optional[str] = None
    address: Optional[AddressSchema] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    parent_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    contact_ids: Optional[list[UUID]] = None


class ContactSummary(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    id: UUID
    name: str
    segment: Optional[str]
    size: Optional[str]

    model_config = {"from_attributes": True}


class AccountResponse(BaseModel):
    id: UUID
    name: str
    cnpj: Optional[str]
    segment: Optional[str]
    size: Optional[str]
    address: Optional[dict[str, Any]]
    website: Optional[str]
    notes: Optional[str]
    is_active: bool
    parent_id: Optional[UUID]
    owner_id: Optional[UUID]
    contacts: list[ContactSummary]
    children: list[AccountSummary]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    updated_by: Optional[UUID]

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    id: UUID
    name: str
    cnpj: Optional[str]
    segment: Optional[str]
    size: Optional[str]
    is_active: bool
    parent_id: Optional[UUID]
    owner_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountFilters(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    segment: Optional[str] = None
    is_active: Optional[bool] = True
    owner_id: Optional[UUID] = None
