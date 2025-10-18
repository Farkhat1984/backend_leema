"""Order schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class OrderItemResponse(BaseModel):
    """Order item details"""
    id: int
    product_id: int
    product_name: Optional[str] = None
    shop_id: int
    shop_name: Optional[str] = None
    quantity: int
    price_at_purchase: float
    subtotal: float
    
    model_config = {"from_attributes": True}


class OrderBase(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)
    rental_days: Optional[int] = Field(default=None, ge=1)


class OrderCreate(OrderBase):
    pass


class OrderCreateFromCart(BaseModel):
    """Create order from cart"""
    payment_method: str = Field(default="paypal", pattern="^(paypal|balance)$")


class OrderResponse(BaseModel):
    id: int
    order_number: str
    user_id: int
    order_type: str
    status: str
    total_amount: float
    
    # Legacy fields
    product_id: Optional[int] = None
    shop_id: Optional[int] = None
    quantity: int = 1
    
    rental_days: Optional[int] = None
    rental_start_date: Optional[datetime] = None
    rental_end_date: Optional[datetime] = None
    transaction_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Order items (for multi-product orders)
    items: List[OrderItemResponse] = []
    
    # Nested info for single-product orders (backwards compatibility)
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    shop_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Paginated list of orders"""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int
