from pydantic import BaseModel, Field, field_validator, field_serializer, HttpUrl
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
                # Allow http(s) absolute URLs or relative /uploads/ paths
                if not url or not isinstance(url, str):
                    raise ValueError(f'Invalid image URL: {url}')
                # Accept absolute URLs or relative paths
                if not (url.startswith(('http://', 'https://')) or url.startswith('/uploads/') or url.startswith('uploads/')):
                    raise ValueError(f'Invalid image URL: "{url}" - must start with http://, https://, /uploads/ or uploads/')
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

    @field_serializer('images')
    def serialize_images(self, images: Optional[List[str]], _info) -> Optional[List[str]]:
        """Convert relative image URLs to absolute URLs"""
        if not images:
            return images
        
        from app.config import settings
        base_url = settings.UPLOAD_URL_PREFIX if settings.UPLOAD_URL_PREFIX else "https://api.leema.kz"
        
        result = []
        for img in images:
            # If already absolute URL, keep it
            if img.startswith(('http://', 'https://')):
                result.append(img)
            # If relative URL, make it absolute
            elif img.startswith('/'):
                result.append(f"{base_url}{img}")
            else:
                # Assume it's just filename
                result.append(f"{base_url}/uploads/products/{img}")
        return result

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int
