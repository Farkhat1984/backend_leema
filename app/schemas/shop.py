from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List
import re


def validate_phone_number(value: Optional[str]) -> Optional[str]:
    """Validate and normalize phone number for international format (+XXXXXXXXXXXX)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Handle None and empty strings
    if not value:
        logger.info(f"📞 Phone number is empty, returning None")
        return None
    
    # Handle empty strings with only whitespace
    if isinstance(value, str) and not value.strip():
        logger.info(f"📞 Phone number is whitespace only, returning None")
        return None
    
    logger.info(f"📞 Validating phone number: '{value}'")
    
    # Remove all spaces, dashes, parentheses, underscores
    cleaned = re.sub(r'[\s\-\(\)_]', '', value)
    
    logger.info(f"📞 Cleaned phone number: '{cleaned}'")
    
    # If cleaned version is empty or just a + sign, return None
    if not cleaned or cleaned == '+':
        logger.info(f"📞 Phone number is empty after cleaning, returning None")
        return None
    
    # Must start with + and have 7-15 digits after (international format)
    # Support multiple formats:
    # +7XXXXXXXXXX (Kazakhstan - 11 digits total)
    # +1XXXXXXXXXX (USA - 11 digits total)  
    # +44XXXXXXXXX (UK - 12-13 digits total)
    # +86XXXXXXXXXXX (China - 13 digits total)
    # etc.
    if not re.match(r'^\+\d{7,15}$', cleaned):
        logger.error(f"❌ Phone validation failed for: '{cleaned}'")
        raise ValueError('Номер телефона должен быть в международном формате с кодом страны, например: +7XXXXXXXXXX, +1XXXXXXXXXX')
    
    logger.info(f"✅ Phone validation passed: '{cleaned}'")
    return cleaned


class ShopBase(BaseModel):
    email: EmailStr
    shop_name: str = Field(..., min_length=1, max_length=255)
    owner_name: str = Field(..., min_length=1, max_length=255)


class ShopCreate(ShopBase):
    google_id: str
    description: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    whatsapp_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = True
    
    @field_validator('phone', 'whatsapp_number', mode='before')
    @classmethod
    def validate_phones(cls, v):
        return validate_phone_number(v)


class ShopUpdate(BaseModel):
    shop_name: Optional[str] = Field(None, min_length=1, max_length=255)
    owner_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    whatsapp_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    
    @field_validator('phone', 'whatsapp_number', mode='before')
    @classmethod
    def validate_phones(cls, v):
        return validate_phone_number(v)


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
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None
    balance: float = 0
    is_approved: bool
    is_active: bool
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopListItem(BaseModel):
    id: int
    shop_name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None  # Alias for avatar_url
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None
    products_count: int = 0
    is_approved: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ShopList(BaseModel):
    shops: List[ShopListItem]
    total: int
    page: int = 1
    page_size: int = 50
