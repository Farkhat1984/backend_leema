from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    APP_NAME: str = "Fashion AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fashion_platform.db"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"  # https://api.leema.kz/api/v1/auth/google/callback in production

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

    # Platform settings defaults
    DEFAULT_USER_GENERATION_PRICE: float = 1.0
    DEFAULT_USER_TRY_ON_PRICE: float = 0.5
    DEFAULT_USER_FREE_GENERATIONS: int = 3
    DEFAULT_USER_FREE_TRY_ONS: int = 5
    DEFAULT_SHOP_PRODUCT_RENT_PRICE: float = 10.0
    DEFAULT_SHOP_MIN_RENT_MONTHS: int = 1
    DEFAULT_SHOP_COMMISSION_RATE: float = 10.0  # %
    DEFAULT_REFUND_PERIOD_DAYS: int = 14

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://www.leema.kz",
        "https://leema.kz",
        "https://api.leema.kz"
    ]
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend URL for redirects (https://www.leema.kz in production)

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: str = "60/minute"


settings = Settings()
