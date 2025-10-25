from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.product import Product, ModerationStatus
from app.models.moderation import ModerationQueue
from app.schemas.product import ProductCreate, ProductUpdate
from datetime import timedelta
from typing import Optional, List, Tuple
from decimal import Decimal
import logging
from app.core.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class ProductService:
    """Product service for business logic"""

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, shop_id: int, product_data: ProductCreate) -> Product:
        """Create new product (pending moderation)"""
        product = Product(
            shop_id=shop_id,
            name=product_data.name,
            description=product_data.description,
            characteristics=product_data.characteristics,
            price=product_data.price,
            category_id=product_data.category_id,
            images=product_data.images,
            moderation_status=ModerationStatus.PENDING,
            is_active=False,
        )
        db.add(product)
        await db.flush()  # Get product ID

        # Add to moderation queue
        moderation = ModerationQueue(product_id=product.id)
        db.add(moderation)

        await db.commit()
        await db.refresh(product)
        logger.info(f"Product created: {product.name} (pending moderation)")
        return product

    @staticmethod
    async def update(
        db: AsyncSession, product_id: int, product_data: ProductUpdate
    ) -> Optional[Product]:
        """Update product"""
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return None

        logger.info(f"Updating product {product_id}")
        logger.info(f"Current images: {product.images}")
        logger.info(f"New images from request: {product_data.images}")

        if product_data.name:
            product.name = product_data.name
        if product_data.description is not None:
            product.description = product_data.description
        if product_data.price is not None:
            product.price = product_data.price
        if product_data.characteristics is not None:
            product.characteristics = product_data.characteristics
        if product_data.category_id is not None:
            product.category_id = product_data.category_id
            logger.info(f"Category updated to: {product.category_id}")
        # Update images even if it's an empty list (to allow deletion of all images)
        if product_data.images is not None:
            product.images = product_data.images if product_data.images else []
            logger.info(f"Images updated to: {product.images}")

        await db.commit()
        await db.refresh(product)
        logger.info(f"Product {product_id} updated successfully. Final images: {product.images}")
        return product

    @staticmethod
    async def delete(db: AsyncSession, product_id: int) -> bool:
        """Delete product (soft delete if has orders, hard delete otherwise)"""
        from app.models.order import OrderItem
        
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return False

        # Check if product has order items (already purchased)
        order_items_result = await db.execute(
            select(OrderItem).where(OrderItem.product_id == product_id).limit(1)
        )
        has_orders = order_items_result.scalar_one_or_none() is not None
        
        if has_orders:
            # Soft delete: deactivate and mark as rejected
            product.is_active = False
            product.moderation_status = ModerationStatus.REJECTED
            product.moderation_notes = "Удалено владельцем магазина"
            await db.commit()
            logger.info(f"Product soft-deleted (has orders): {product_id}")
        else:
            # Hard delete: remove from database permanently
            # First, explicitly delete moderation queue entry if exists
            moderation_result = await db.execute(
                select(ModerationQueue).where(ModerationQueue.product_id == product_id)
            )
            moderation = moderation_result.scalar_one_or_none()
            if moderation:
                await db.delete(moderation)
                logger.info(f"Deleted moderation queue entry for product {product_id}")
            
            # Now delete the product
            await db.delete(product)
            await db.commit()
            logger.info(f"Product hard-deleted (no orders): {product_id}")
        
        return True

    @staticmethod
    async def get_active_products(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[Product], int]:
        """Get active approved products"""
        query = select(Product).where(
            and_(Product.is_active == True, Product.moderation_status == ModerationStatus.APPROVED)
        )

        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get products
        query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        products = result.scalars().all()

        return products, total

    @staticmethod
    async def increment_views(db: AsyncSession, product_id: int):
        """Increment product views"""
        product = await ProductService.get_by_id(db, product_id)
        if product:
            product.views_count += 1
            await db.commit()

    @staticmethod
    async def increment_try_ons(db: AsyncSession, product_id: int):
        """Increment product try-ons"""
        product = await ProductService.get_by_id(db, product_id)
        if product:
            product.try_ons_count += 1
            await db.commit()

    @staticmethod
    async def increment_purchases(db: AsyncSession, product_id: int):
        """Increment product purchases"""
        product = await ProductService.get_by_id(db, product_id)
        if product:
            product.purchases_count += 1
            await db.commit()

    @staticmethod
    async def set_rent_period(
        db: AsyncSession, product_id: int, months: int
    ) -> Optional[Product]:
        """Set product rent period"""
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return None

        product.rent_expires_at = utc_now() + timedelta(days=30 * months)
        product.is_active = True
        await db.commit()
        await db.refresh(product)
        logger.info(f"Product {product_id} rent set for {months} months")
        return product

    @staticmethod
    async def approve_product(
        db: AsyncSession, product_id: int, admin_id: int, notes: Optional[str] = None
    ) -> Optional[Product]:
        """Approve product (admin) - charges shop for approval"""
        from app.services.shop_service import shop_service
        from app.services.settings_service import settings_service
        from app.models.transaction import Transaction, TransactionType, TransactionStatus

        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return None

        # Get shop
        shop = await shop_service.get_by_id(db, product.shop_id)
        if not shop:
            return None

        # Get approval fee from settings and normalize to Decimal
        approval_fee = await settings_service.get_setting_float(db, "shop_approval_fee", 5.0)
        approval_fee_decimal = Decimal(str(approval_fee))

        # Check shop balance using Decimal comparison
        if shop.balance < approval_fee_decimal:
            raise ValueError(
                f"Недостаточно средств на балансе магазина '{shop.shop_name}'. "
                f"Требуется: ${approval_fee:.2f}, доступно: ${shop.balance:.2f}"
            )

        # Charge shop
        shop.balance -= approval_fee_decimal

        # Create transaction record
        transaction = Transaction(
            shop_id=shop.id,
            type=TransactionType.APPROVAL_FEE,
            amount=-approval_fee_decimal,
            status=TransactionStatus.COMPLETED,
            extra_data={
                "product_id": product_id,
                "product_name": product.name,
                "admin_id": admin_id,
                "description": f"Плата за одобрение товара: {product.name}"
            }
        )
        db.add(transaction)

        # Approve product and activate it
        product.moderation_status = ModerationStatus.APPROVED
        product.is_active = True  # Automatically activate approved products
        product.moderation_notes = notes

        # Update moderation queue
        result = await db.execute(
            select(ModerationQueue).where(ModerationQueue.product_id == product_id)
        )
        moderation = result.scalar_one_or_none()
        if moderation:
            moderation.reviewed_at = utc_now()
            moderation.reviewed_by = admin_id
            moderation.notes = notes

        await db.commit()
        await db.refresh(product)
        logger.info(f"Product approved: {product_id}, charged ${approval_fee} from shop {shop.id}")
        return product

    @staticmethod
    async def reject_product(
        db: AsyncSession, product_id: int, admin_id: int, notes: str
    ) -> Optional[Product]:
        """Reject product (admin)"""
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return None

        product.moderation_status = ModerationStatus.REJECTED
        product.moderation_notes = notes

        # Update moderation queue
        result = await db.execute(
            select(ModerationQueue).where(ModerationQueue.product_id == product_id)
        )
        moderation = result.scalar_one_or_none()
        if moderation:
            moderation.reviewed_at = utc_now()
            moderation.reviewed_by = admin_id
            moderation.notes = notes

        await db.commit()
        await db.refresh(product)
        logger.info(f"Product rejected: {product_id}")
        return product


product_service = ProductService()
