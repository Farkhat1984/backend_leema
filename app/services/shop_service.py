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
        """Create new shop - requires admin approval by default"""
        logger.info(f"Creating shop with data: phone={shop_data.phone}, whatsapp={shop_data.whatsapp_number}")
        shop = Shop(
            google_id=shop_data.google_id,
            email=shop_data.email,
            shop_name=shop_data.shop_name,
            owner_name=shop_data.owner_name,
            description=shop_data.description,
            avatar_url=shop_data.avatar_url,
            phone=shop_data.phone,
            whatsapp_number=shop_data.whatsapp_number,
            address=shop_data.address,
            is_approved=False,  # Requires admin approval
        )
        db.add(shop)
        await db.commit()
        await db.refresh(shop)
        logger.info(f"Shop created (pending approval): {shop.shop_name}, phone={shop.phone}, whatsapp={shop.whatsapp_number}")
        return shop

    @staticmethod
    async def update(db: AsyncSession, shop_id: int, shop_data: ShopUpdate) -> Optional[Shop]:
        """Update shop"""
        logger.info(f"🔍 [SHOP UPDATE] Starting update for shop {shop_id}")
        logger.info(f"📦 [SHOP UPDATE] Received data (all fields): {shop_data.model_dump()}")
        logger.info(f"📦 [SHOP UPDATE] Received data (exclude_unset): {shop_data.model_dump(exclude_unset=True)}")
        
        shop = await ShopService.get_by_id(db, shop_id)
        if not shop:
            logger.error(f"❌ [SHOP UPDATE] Shop {shop_id} not found for update")
            return None

        logger.info(f"📊 [SHOP UPDATE] Current shop state BEFORE update:")
        logger.info(f"   - Phone: {shop.phone}")
        logger.info(f"   - WhatsApp: {shop.whatsapp_number}")
        logger.info(f"   - Avatar: {shop.avatar_url}")

        # Track if critical fields are being updated (re-submission after rejection)
        is_resubmission = False
        if shop.rejection_reason and (shop_data.phone or shop_data.address or shop_data.description):
            is_resubmission = True

        # КЛЮЧЕВАЯ ЛОГИКА: используем exclude_unset чтобы обновлять ТОЛЬКО переданные поля
        update_dict = shop_data.model_dump(exclude_unset=True)
        
        logger.info(f"🔄 [SHOP UPDATE] Fields to update (exclude_unset): {list(update_dict.keys())}")
        logger.info(f"🔄 [SHOP UPDATE] Update values: {update_dict}")
        
        for field, value in update_dict.items():
            old_value = getattr(shop, field)
            logger.info(f"   ✏️ Setting {field}: {old_value} -> {value}")
            setattr(shop, field, value)
            
            # Verify the field was actually set
            new_value = getattr(shop, field)
            if new_value != value:
                logger.warning(f"   ⚠️ Field {field} was set to {value} but is now {new_value}")

        # Clear rejection reason if this is a resubmission
        if is_resubmission:
            shop.rejection_reason = None
            logger.info(f"🔄 [SHOP UPDATE] Shop {shop.shop_name} resubmitted after rejection - cleared rejection reason")

        # Commit changes
        logger.info(f"💾 [SHOP UPDATE] Committing changes to database...")
        await db.commit()
        await db.refresh(shop)
        
        logger.info(f"✅ [SHOP UPDATE] Shop {shop_id} updated successfully")
        logger.info(f"📊 [SHOP UPDATE] Final shop state AFTER update:")
        logger.info(f"   - Phone: {shop.phone}")
        logger.info(f"   - WhatsApp: {shop.whatsapp_number}")
        logger.info(f"   - Avatar: {shop.avatar_url}")
        
        # Verify in database
        logger.info(f"🔍 [SHOP UPDATE] Verifying data was persisted...")
        verification_shop = await ShopService.get_by_id(db, shop_id)
        if verification_shop:
            logger.info(f"✅ [SHOP UPDATE] Verification - data in DB:")
            logger.info(f"   - Phone: {verification_shop.phone}")
            logger.info(f"   - WhatsApp: {verification_shop.whatsapp_number}")
            logger.info(f"   - Avatar: {verification_shop.avatar_url}")
        
        return shop

    @staticmethod
    async def get_products(
        db: AsyncSession, shop_id: int, skip: int = 0, limit: int = 50
    ) -> List[Product]:
        """Get shop products (all products, not just active)"""
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

    @staticmethod
    async def get_shops_list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        is_active: Optional[bool] = None
    ):
        """Get list of approved shops with active products"""
        from sqlalchemy import or_, desc, asc, case
        
        # Subquery to count active products per shop
        products_count_subquery = (
            select(
                Product.shop_id,
                func.count(Product.id).label("products_count")
            )
            .where(Product.is_active == True)
            .group_by(Product.shop_id)
            .subquery()
        )
        
        # Main query
        shops_query = (
            select(
                Shop,
                func.coalesce(products_count_subquery.c.products_count, 0).label("products_count")
            )
            .outerjoin(products_count_subquery, Shop.id == products_count_subquery.c.shop_id)
            .where(Shop.is_approved == True)
        )
        
        # Filter by is_active if provided
        if is_active is not None:
            shops_query = shops_query.where(Shop.is_active == is_active)
        
        # Filter: only shops with active products
        shops_query = shops_query.where(
            func.coalesce(products_count_subquery.c.products_count, 0) > 0
        )
        
        # Search filter
        if query:
            shops_query = shops_query.where(
                or_(
                    Shop.shop_name.ilike(f"%{query}%"),
                    Shop.description.ilike(f"%{query}%")
                )
            )
        
        # Sorting
        sort_column = products_count_subquery.c.products_count
        if sort_by == "created_at":
            sort_column = Shop.created_at
        elif sort_by == "shop_name":
            sort_column = Shop.shop_name
        elif sort_by == "products_count":
            sort_column = func.coalesce(products_count_subquery.c.products_count, 0)
        
        if sort_order == "asc":
            shops_query = shops_query.order_by(asc(sort_column))
        else:
            shops_query = shops_query.order_by(desc(sort_column))
        
        # Count total
        count_query = (
            select(func.count(Shop.id.distinct()))
            .select_from(Shop)
            .outerjoin(products_count_subquery, Shop.id == products_count_subquery.c.shop_id)
            .where(Shop.is_approved == True)
            .where(func.coalesce(products_count_subquery.c.products_count, 0) > 0)
        )
        
        # Filter by is_active in count query
        if is_active is not None:
            count_query = count_query.where(Shop.is_active == is_active)
        
        if query:
            count_query = count_query.where(
                or_(
                    Shop.shop_name.ilike(f"%{query}%"),
                    Shop.description.ilike(f"%{query}%")
                )
            )
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Pagination
        shops_query = shops_query.offset(skip).limit(limit)
        
        # Execute
        result = await db.execute(shops_query)
        rows = result.all()
        
        # Build response
        shops_with_count = []
        for shop, products_count in rows:
            shop_dict = {
                "id": shop.id,
                "shop_name": shop.shop_name,
                "description": shop.description,
                "avatar_url": shop.avatar_url,
                "logo_url": shop.avatar_url,  # Alias
                "products_count": products_count,
                "is_approved": shop.is_approved,
                "is_active": shop.is_active,
                "created_at": shop.created_at
            }
            shops_with_count.append(shop_dict)
        
        return shops_with_count, total


    @staticmethod
    async def approve_shop(db: AsyncSession, shop_id: int, admin_id: int, notes: Optional[str] = None) -> Optional[Shop]:
        """Approve shop - allow them to create products and activate the shop"""
        shop = await ShopService.get_by_id(db, shop_id)
        if not shop:
            return None
        
        shop.is_approved = True
        shop.is_active = True  # Activate shop when approved
        shop.rejection_reason = None  # Clear any previous rejection
        await db.commit()
        await db.refresh(shop)
        
        logger.info(f"Shop {shop_id} approved and activated by admin {admin_id}")
        return shop

    @staticmethod
    async def reject_shop(db: AsyncSession, shop_id: int, admin_id: int, reason: str) -> Optional[Shop]:
        """Reject shop registration with reason"""
        shop = await ShopService.get_by_id(db, shop_id)
        if not shop:
            return None
        
        shop.is_approved = False
        shop.rejection_reason = reason
        await db.commit()
        await db.refresh(shop)
        
        logger.info(f"Shop {shop_id} rejected by admin {admin_id}: {reason}")
        return shop

    @staticmethod
    async def delete_shop(db: AsyncSession, shop_id: int) -> bool:
        """Delete shop and all associated products"""
        shop = await ShopService.get_by_id(db, shop_id)
        if not shop:
            return False
        
        # Delete all products first
        await db.execute(
            select(Product).where(Product.shop_id == shop_id)
        )
        products_result = await db.execute(
            select(Product).where(Product.shop_id == shop_id)
        )
        products = products_result.scalars().all()
        
        for product in products:
            await db.delete(product)
        
        # Delete shop
        await db.delete(shop)
        await db.commit()
        
        logger.info(f"Shop {shop_id} deleted with {len(products)} products")
        return True


shop_service = ShopService()
