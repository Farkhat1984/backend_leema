from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import async_session_maker
from app.models.product import Product
from app.models.shop import Shop
from app.core.email import email_service
from datetime import timedelta
import logging
from app.core.datetime_utils import utc_now

logger = logging.getLogger(__name__)


async def check_expiring_rents():
    """Check for products with expiring rent and send notifications"""
    async with async_session_maker() as db:
        try:
            # Get products expiring in 3 days
            three_days_from_now = utc_now() + timedelta(days=3)
            three_days_ago = utc_now() + timedelta(days=2)  # To avoid sending multiple times

            result = await db.execute(
                select(Product, Shop)
                .join(Shop, Product.shop_id == Shop.id)
                .where(
                    and_(
                        Product.is_active == True,
                        Product.rent_expires_at.is_not(None),
                        Product.rent_expires_at <= three_days_from_now,
                        Product.rent_expires_at > three_days_ago
                    )
                )
            )

            products_shops = result.all()

            for product, shop in products_shops:
                days_left = (product.rent_expires_at - utc_now()).days
                await email_service.send_rent_expiring_notification(
                    shop.email,
                    shop.shop_name,
                    product.name,
                    days_left
                )
                logger.info(f"Sent rent expiring notification for product {product.id} to {shop.email}")

        except Exception as e:
            logger.error(f"Error checking expiring rents: {e}")


async def deactivate_expired_products():
    """Deactivate products with expired rent"""
    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(Product).where(
                    and_(
                        Product.is_active == True,
                        Product.rent_expires_at.is_not(None),
                        Product.rent_expires_at <= utc_now()
                    )
                )
            )

            products = result.scalars().all()

            for product in products:
                product.is_active = False
                logger.info(f"Deactivated expired product {product.id}")

            if products:
                await db.commit()
                logger.info(f"Deactivated {len(products)} expired products")

        except Exception as e:
            logger.error(f"Error deactivating expired products: {e}")
