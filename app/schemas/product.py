from pydantic import BaseModel, Field, field_validator, HttpUrl
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class ModerationStatusEnum(str, Enum):
    """Product moderation status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=2000, description="Product description")
    price: float = Field(..., gt=0, le=1000000, description="Product price (must be positive, max 1M)")
    characteristics: Optional[Dict] = Field(None, description="Product characteristics as JSON")


class ProductCreate(ProductBase):
    images: Optional[List[str]] = Field(None, max_length=10, description="Product image URLs (max 10)")
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        """Validate image URLs"""
        if v:
            if len(v) > 10:
                raise ValueError('Maximum 10 images allowed')
            # Check if URLs are valid (basic check)
            for url in v:
                if not url.startswith(('http://', 'https://', '/uploads/')):
                    raise ValueError(f'Invalid image URL: {url}')
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[float] = Field(None, gt=0)
    characteristics: Optional[Dict] = None
    images: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: int
    shop_id: int
    images: Optional[List[str]] = None
    rent_expires_at: Optional[datetime] = None
    is_active: bool
    moderation_status: ModerationStatusEnum
    moderation_notes: Optional[str] = None
    views_count: int
    try_ons_count: int
    purchases_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int
