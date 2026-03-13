import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ──────────────── Auth ────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve conter ao menos uma letra maiúscula")
        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter ao menos um número")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve conter ao menos uma letra maiúscula")
        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter ao menos um número")
        return v


# ──────────────── Permissions ────────────────

class PermissionSchema(BaseModel):
    module: str
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False

    model_config = {"from_attributes": True}


class PermissionResponse(PermissionSchema):
    id: UUID


# ──────────────── Roles ────────────────

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: list[PermissionSchema] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[list[PermissionSchema]] = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    permissions: list[PermissionResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────── Users ────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role_ids: list[UUID] = []

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role_ids: Optional[list[UUID]] = None


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    is_active: bool
    roles: list[RoleResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    id: UUID
    name: str
    email: str
    is_active: bool
    roles: list[str]

    model_config = {"from_attributes": True}
