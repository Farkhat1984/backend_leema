from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRoleEnum(str, Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255, description="User display name")


class UserCreate(UserBase):
    google_id: str
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = None


class UserBalance(BaseModel):
    balance: float
    free_generations_left: int
    free_try_ons_left: int


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    balance: float = Field(..., ge=0, description="User balance (non-negative)")
    free_generations_left: int = Field(..., ge=0, description="Remaining free generations")
    free_try_ons_left: int = Field(..., ge=0, description="Remaining free try-ons")
    role: UserRoleEnum
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
