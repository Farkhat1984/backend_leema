"""Cart schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=100)


class ProductInCart(BaseModel):
    """Product information for cart item"""
    id: int
    name: str
    price: float
    images: Optional[List[str]] = None
    shop_id: int
    shop_name: Optional[str] = None
    is_active: bool
    
    model_config = {"from_attributes": True}


class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    product_id: int
    quantity: int
    added_at: datetime
    
    # Nested product info
    product: Optional[ProductInCart] = None
    subtotal: float = 0.0  # price * quantity
    
    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: int
    user_id: int
    items: List[CartItemResponse] = []
    total_items: int = 0
    total_price: float = 0.0
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
