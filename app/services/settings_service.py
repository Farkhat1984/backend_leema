from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.settings import PlatformSettings
from app.config import settings as config
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SettingsService:
    """Platform settings service"""

    @staticmethod
    async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
        """Get setting value by key"""
        result = await db.execute(select(PlatformSettings).where(PlatformSettings.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    @staticmethod
    async def get_setting_float(db: AsyncSession, key: str, default: float) -> float:
        """Get setting as float"""
        value = await SettingsService.get_setting(db, key)
        try:
            return float(value) if value else default
        except ValueError:
            return default

    @staticmethod
    async def get_setting_int(db: AsyncSession, key: str, default: int) -> int:
        """Get setting as int"""
        value = await SettingsService.get_setting(db, key)
        try:
            return int(value) if value else default
        except ValueError:
            return default

    @staticmethod
    async def set_setting(db: AsyncSession, key: str, value: str, description: Optional[str] = None):
        """Set or update setting"""
        result = await db.execute(select(PlatformSettings).where(PlatformSettings.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = PlatformSettings(key=key, value=value, description=description)
            db.add(setting)

        await db.commit()
        logger.info(f"Setting updated: {key} = {value}")

    @staticmethod
    async def get_all_settings(db: AsyncSession) -> dict:
        """Get all settings as dict"""
        result = await db.execute(select(PlatformSettings))
        settings_list = result.scalars().all()
        return {s.key: s.value for s in settings_list}

    @staticmethod
    async def initialize_default_settings(db: AsyncSession):
        """Initialize default platform settings"""
        defaults = {
            "user_generation_price": (str(config.DEFAULT_USER_GENERATION_PRICE), "Price per generation (USD)"),
            "user_try_on_price": (str(config.DEFAULT_USER_TRY_ON_PRICE), "Price per try-on (USD)"),
            "user_free_generations": (str(config.DEFAULT_USER_FREE_GENERATIONS), "Free generations for new users"),
            "user_free_try_ons": (str(config.DEFAULT_USER_FREE_TRY_ONS), "Free try-ons for new users"),
            "shop_product_rent_price": (str(config.DEFAULT_SHOP_PRODUCT_RENT_PRICE), "Product rent price per month (USD)"),
            "shop_min_rent_months": (str(config.DEFAULT_SHOP_MIN_RENT_MONTHS), "Minimum rent period (months)"),
            "shop_commission_rate": (str(config.DEFAULT_SHOP_COMMISSION_RATE), "Platform commission rate (%)"),
            "refund_period_days": (str(config.DEFAULT_REFUND_PERIOD_DAYS), "Refund request period (days)"),
        }

        for key, (value, description) in defaults.items():
            existing = await SettingsService.get_setting(db, key)
            if not existing:
                await SettingsService.set_setting(db, key, value, description)

        logger.info("Default settings initialized")


settings_service = SettingsService()
