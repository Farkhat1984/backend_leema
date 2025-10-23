"""
Wardrobe schemas - User's personal clothing collection
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class WardrobeItemSourceEnum(str, Enum):
    """Source of the wardrobe item"""
    SHOP_PRODUCT = "shop_product"
    GENERATED = "generated"
    UPLOADED = "uploaded"
    PURCHASED = "purchased"


class WardrobeItemBase(BaseModel):
    """Base wardrobe item fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    description: Optional[str] = Field(None, max_length=2000, description="Item description")
    characteristics: Optional[Dict] = Field(None, description="Item characteristics (size, color, etc.)")
    is_favorite: bool = Field(default=False, description="Is this item marked as favorite")
    folder: Optional[str] = Field(None, max_length=100, description="Folder/collection name for organization")


class WardrobeItemCreate(WardrobeItemBase):
    """Create wardrobe item (user upload)"""
    images: Optional[List[str]] = Field(None, max_length=5, description="Image URLs (max 5)")
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        """Validate image URLs"""
        if v:
            if len(v) > 5:
                raise ValueError('Maximum 5 images allowed per wardrobe item')
            for url in v:
                if not url or not isinstance(url, str):
                    raise ValueError(f'Invalid image URL: {url}')
                # Accept absolute URLs or relative paths
                if not (url.startswith(('http://', 'https://')) or url.startswith('/uploads/') or url.startswith('uploads/')):
                    raise ValueError(f'Invalid image URL: "{url}" - must start with http://, https://, /uploads/ or uploads/')
        return v


class WardrobeItemFromShop(BaseModel):
    """Create wardrobe item from shop product - optional customization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Custom name (overrides product name)")
    description: Optional[str] = Field(None, max_length=2000, description="Custom description")
    folder: Optional[str] = Field(None, max_length=100, description="Folder to add item to")
    is_favorite: bool = Field(default=False, description="Mark as favorite")


class WardrobeItemFromGeneration(BaseModel):
    """Create wardrobe item from AI generation - optional customization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Custom name")
    description: Optional[str] = Field(None, max_length=2000, description="Custom description")
    folder: Optional[str] = Field(None, max_length=100, description="Folder to add item to")
    is_favorite: bool = Field(default=False, description="Mark as favorite")


class WardrobeItemUpdate(BaseModel):
    """Update wardrobe item - all fields optional"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    characteristics: Optional[Dict] = None
    images: Optional[List[str]] = Field(None, max_length=5)
    is_favorite: Optional[bool] = None
    folder: Optional[str] = Field(None, max_length=100)
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        """Validate image URLs"""
        if v is not None:
            if len(v) > 5:
                raise ValueError('Maximum 5 images allowed per wardrobe item')
            for url in v:
                if not url or not isinstance(url, str):
                    raise ValueError(f'Invalid image URL: {url}')
                if not (url.startswith(('http://', 'https://')) or url.startswith('/uploads/') or url.startswith('uploads/')):
                    raise ValueError(f'Invalid image URL: "{url}"')
        return v


class WardrobeItemResponse(WardrobeItemBase):
    """Wardrobe item response with all fields"""
    id: int
    user_id: int
    source: WardrobeItemSourceEnum
    original_product_id: Optional[int] = None
    generation_id: Optional[int] = None
    images: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WardrobeListResponse(BaseModel):
    """Paginated wardrobe list response"""
    items: List[WardrobeItemResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class WardrobeItemDeleted(BaseModel):
    """Response after deleting a wardrobe item"""
    message: str
    id: int
