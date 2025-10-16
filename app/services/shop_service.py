from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.shop import Shop
from app.models.product import Product
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.shop import ShopCreate, ShopUpdate, ShopAnalytics
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class ShopService:
    """Shop service for business logic"""

    @staticmethod
    async def get_by_id(db: AsyncSession, shop_id: int) -> Optional[Shop]:
        """Get shop by ID"""
        result = await db.execute(select(Shop).where(Shop.id == shop_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_google_id(db: AsyncSession, google_id: str) -> Optional[Shop]:
        """Get shop by Google ID"""
        result = await db.execute(select(Shop).where(Shop.google_id == google_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[Shop]:
        """Get shop by email"""
        result = await db.execute(select(Shop).where(Shop.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, shop_data: ShopCreate) -> Shop:
        """Create new shop"""
        shop = Shop(
            google_id=shop_data.google_id,
            email=shop_data.email,
            shop_name=shop_data.shop_name,
            owner_name=shop_data.owner_name,
            description=shop_data.description,
            avatar_url=shop_data.avatar_url,
        )
        db.add(shop)
        await db.commit()
        await db.refresh(shop)
        logger.info(f"Shop created: {shop.shop_name}")
        return shop

    @staticmethod
    async def update(db: AsyncSession, shop_id: int, shop_data: ShopUpdate) -> Optional[Shop]:
        """Update shop"""
        shop = await ShopService.get_by_id(db, shop_id)
        if not shop:
            return None

        if shop_data.shop_name:
            shop.shop_name = shop_data.shop_name
        if shop_data.description is not None:
            shop.description = shop_data.description
        if shop_data.avatar_url is not None:
            shop.avatar_url = shop_data.avatar_url

        await db.commit()
        await db.refresh(shop)
        return shop

    @staticmethod
    async def get_products(
        db: AsyncSession, shop_id: int, skip: int = 0, limit: int = 50
    ) -> List[Product]:
        """Get shop products"""
        result = await db.execute(
            select(Product)
            .where(Product.shop_id == shop_id)
            .order_by(Product.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_analytics(db: AsyncSession, shop_id: int) -> ShopAnalytics:
        """Get shop analytics"""
        # Count products
        total_products_result = await db.execute(
            select(func.count(Product.id)).where(Product.shop_id == shop_id)
        )
        total_products = total_products_result.scalar() or 0

        active_products_result = await db.execute(
            select(func.count(Product.id)).where(
                Product.shop_id == shop_id,
                Product.is_active == True
            )
        )
        active_products = active_products_result.scalar() or 0

        # Sum stats
        stats_result = await db.execute(
            select(
                func.sum(Product.views_count),
                func.sum(Product.try_ons_count),
                func.sum(Product.purchases_count)
            ).where(Product.shop_id == shop_id)
        )
        stats = stats_result.first()

        total_views = stats[0] or 0
        total_try_ons = stats[1] or 0
        total_purchases = stats[2] or 0

        # Calculate revenue from transactions
        revenue_result = await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.shop_id == shop_id,
                Transaction.status == TransactionStatus.COMPLETED
            )
        )
        total_revenue = float(revenue_result.scalar() or 0)

        return ShopAnalytics(
            total_products=total_products,
            active_products=active_products,
            total_views=total_views,
            total_try_ons=total_try_ons,
            total_purchases=total_purchases,
            total_revenue=total_revenue,
        )

    @staticmethod
    async def get_transactions(
        db: AsyncSession, shop_id: int, skip: int = 0, limit: int = 50
    ) -> List[Transaction]:
        """Get shop transactions"""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.shop_id == shop_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def add_balance(db: AsyncSession, shop_id: int, amount: float) -> bool:
        """Add balance to shop"""
        from decimal import Decimal

        shop = await ShopService.get_by_id(db, shop_id)
        if not shop:
            return False

        shop.balance = Decimal(str(float(shop.balance) + amount))
        await db.commit()
        await db.refresh(shop)
        logger.info(f"Added {amount} to shop {shop_id} balance. New balance: {shop.balance}")
        return True


shop_service = ShopService()
