from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class ShopBase(BaseModel):
    email: EmailStr
    shop_name: str = Field(..., min_length=1, max_length=255)
    owner_name: str = Field(..., min_length=1, max_length=255)


class ShopCreate(ShopBase):
    google_id: str
    description: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None


class ShopUpdate(BaseModel):
    shop_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None


class ShopAnalytics(BaseModel):
    total_products: int
    active_products: int
    total_views: int
    total_try_ons: int
    total_purchases: int
    total_revenue: float


class ShopResponse(ShopBase):
    id: int
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    balance: float = 0
    is_approved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
