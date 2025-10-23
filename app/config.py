from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    APP_NAME: str = "Fashion AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database - REQUIRED from environment
    DATABASE_URL: str = Field(
        ...,  # No default - must be provided via environment variable
        description="Database connection URL (REQUIRED)"
    )

    # Security - REQUIRED from environment
    SECRET_KEY: str = Field(
        ...,  # No default - must be provided via environment variable
        min_length=64,  # Increased from 32 to 64 for better security
        description="Secret key for JWT tokens (REQUIRED - minimum 64 characters)"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth - REQUIRED from environment
    GOOGLE_CLIENT_ID: str = Field(..., description="Google OAuth Client ID (REQUIRED)")
    GOOGLE_CLIENT_SECRET: str = Field(..., description="Google OAuth Client Secret (REQUIRED)")
    GOOGLE_REDIRECT_URI: str = "https://www.leema.kz/public/auth/callback.html"
    
    # Firebase (for mobile apps) - REQUIRED from environment
    FIREBASE_WEB_API: str = Field(..., description="Firebase Web API Key (REQUIRED)")
    GOOGLE_MOBILE_CLIENT_ID: str = Field(..., description="Google Mobile Client ID (REQUIRED)")
    GOOGLE_MOBILE_CLIENT_SECRET: str = ""  # Optional for mobile OAuth flow
    GOOGLE_ANDROID_CLIENT_ID: str = ""  # Optional - Android-specific client ID

    # Google Gemini AI - REQUIRED from environment
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key (REQUIRED)")
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"  # Latest model 2025

    # PayPal - REQUIRED from environment
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    PAYPAL_CLIENT_ID: str = Field(..., description="PayPal Client ID (REQUIRED)")
    PAYPAL_CLIENT_SECRET: str = Field(..., description="PayPal Client Secret (REQUIRED)")
    PAYPAL_WEBHOOK_ID: str = ""

    # Email (SMTP) - REQUIRED from environment
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = Field(..., description="SMTP User Email (REQUIRED)")
    SMTP_PASSWORD: str = Field(..., description="SMTP Password (REQUIRED)")
    EMAIL_FROM: str = Field(..., description="Email From Address (REQUIRED)")
    EMAIL_FROM_NAME: str = "Fashion AI Platform"

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png", "webp"]
    
    # Upload URL (for production, can be overridden via env)
    UPLOAD_URL_PREFIX: str = ""  # Empty = use API URL, or set to CDN URL

    # Platform settings defaults
    DEFAULT_USER_GENERATION_PRICE: float = 1.0
    DEFAULT_USER_TRY_ON_PRICE: float = 0.5
    DEFAULT_USER_FREE_GENERATIONS: int = 3
    DEFAULT_USER_FREE_TRY_ONS: int = 5
    DEFAULT_SHOP_PRODUCT_RENT_PRICE: float = 10.0
    DEFAULT_SHOP_MIN_RENT_MONTHS: int = 1
    DEFAULT_SHOP_COMMISSION_RATE: float = 10.0  # %
    DEFAULT_SHOP_APPROVAL_FEE: float = 5.0  # Product approval fee
    DEFAULT_REFUND_PERIOD_DAYS: int = 14

    # CORS
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: [
        "https://www.leema.kz",
        "https://leema.kz",
        "https://api.leema.kz",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ])

    # Frontend
    FRONTEND_URL: str = "https://www.leema.kz"
    
    # Backend API URLs (for mobile clients)
    API_BASE_URL: str = "https://api.leema.kz"
    WEBSOCKET_URL: str = "wss://api.leema.kz"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: str = "60/minute"
    
    # Redis (for caching, session storage, token blacklist)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""  # Optional - set if Redis has password
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _assemble_cors_origins(cls, value):
        """Ensure CORS origins env value always becomes a list of strings."""
        if isinstance(value, str):
            # Support JSON-style lists or simple comma-separated strings
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return list(value)
        return value


settings = Settings()
