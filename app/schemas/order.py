"""Order schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class OrderBase(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)
    rental_days: Optional[int] = Field(default=None, ge=1)


class OrderCreate(OrderBase):
    pass


class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    shop_id: int
    order_type: str
    status: str
    amount: float
    quantity: int
    rental_days: Optional[int] = None
    rental_start_date: Optional[datetime] = None
    rental_end_date: Optional[datetime] = None
    transaction_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested product info
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    shop_name: Optional[str] = None

    model_config = {"from_attributes": True}
