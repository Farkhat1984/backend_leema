from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class AdminSettings(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class AdminDashboard(BaseModel):
    total_users: int
    total_shops: int
    total_products: int
    active_products: int
    total_generations: int
    total_revenue: float
    pending_moderation: int
    pending_refunds: int
    total_user_balances: float = 0
    total_shop_balances: float = 0


class ModerationAction(BaseModel):
    action: Optional[str] = Field(None, pattern="^(approve|reject)$")
    notes: Optional[str] = Field(None, max_length=1000)


class RefundAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    admin_notes: Optional[str] = Field(None, max_length=1000)


class RefundRequest(BaseModel):
    transaction_id: int
    reason: str = Field(..., min_length=10, max_length=1000)


class RefundResponse(BaseModel):
    id: int
    transaction_id: int
    user_id: int
    reason: str
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BulkProductAction(BaseModel):
    product_ids: List[int]
    action: str = Field(..., pattern="^(approve|reject|delete|activate|deactivate)$")
    notes: Optional[str] = Field(None, max_length=1000)


class BulkShopAction(BaseModel):
    shop_ids: List[int]
    action: str = Field(..., pattern="^(approve|block)$")
