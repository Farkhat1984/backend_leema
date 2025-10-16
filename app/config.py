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

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fashionuser:Ckdshfh231161@postgres:5432/fashion_platform"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "https://www.leema.kz/api/v1/auth/google/callback"

    # Google Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"  # Latest model 2025

    # PayPal
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
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

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: str = "60/minute"

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
