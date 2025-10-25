from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from enum import Enum


class AccountType(str, Enum):
    """Account type for authentication"""
    USER = "user"
    SHOP = "shop"


class ClientPlatform(str, Enum):
    """Client platform type"""
    WEB = "web"
    MOBILE = "mobile"


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    shop_id: Optional[int] = None
    role: Optional[str] = None
    platform: Optional[ClientPlatform] = None
    account_type: Optional[AccountType] = None


class GoogleAuthRequest(BaseModel):
    code: Optional[str] = Field(None, description="OAuth authorization code (for web)")
    id_token: Optional[str] = Field(None, description="Google ID token (for mobile)")
    account_type: AccountType = Field(..., description="Account type: user or shop")
    platform: ClientPlatform = Field(default=ClientPlatform.MOBILE, description="Client platform: web or mobile")


class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None
    shop: Optional[dict] = None
    account_type: AccountType
    platform: ClientPlatform


class AppleAuthRequest(BaseModel):
    code: Optional[str] = Field(None, description="OAuth authorization code from Apple")
    id_token: Optional[str] = Field(None, description="Apple ID token")
    user_data: Optional[dict] = Field(None, description="User data from Apple (first sign in only)")
    account_type: AccountType = Field(..., description="Account type: user or shop")
    platform: ClientPlatform = Field(default=ClientPlatform.MOBILE, description="Client platform: web or mobile")


class AppleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None
    shop: Optional[dict] = None
    account_type: AccountType
    platform: ClientPlatform


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
