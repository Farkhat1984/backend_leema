"""Order service for managing orders"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order, OrderItem, OrderStatus, OrderType
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.shop import Shop
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.services.cart_service import cart_service
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class OrderService:
    """Service for managing order operations"""

    @staticmethod
    async def create_order_from_cart(
        db: AsyncSession,
        user_id: int,
        cart: Cart
    ) -> Tuple[Optional[Order], Optional[str]]:
        """
        Create order from cart items
        Returns: (Order, error_message)
        """
        if not cart or not cart.items:
            return None, "Cart is empty"
        
        # Validate all products are still available
        total_amount = 0.0
        for cart_item in cart.items:
            product = cart_item.product
            if not product or not product.is_active:
                return None, f"Product {cart_item.product_id} is no longer available"
            
            total_amount += float(product.price) * cart_item.quantity
        
        # Generate order number
        order_number = Order.generate_order_number()
        
        # Create order
        order = Order(
            order_number=order_number,
            user_id=user_id,
            order_type=OrderType.PURCHASE,
            status=OrderStatus.PENDING,
            total_amount=total_amount
        )
        db.add(order)
        await db.flush()  # Get order.id
        
        # Create order items from cart
        for cart_item in cart.items:
            product = cart_item.product
            subtotal = float(product.price) * cart_item.quantity
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                shop_id=product.shop_id,
                quantity=cart_item.quantity,
                price_at_purchase=float(product.price),
                subtotal=subtotal
            )
            db.add(order_item)
        
        await db.commit()
        await db.refresh(order)
        
        logger.info(f"Created order {order_number} from cart for user {user_id}, total: ${total_amount:.2f}")
        return order, None

    @staticmethod
    async def get_order_by_id(
        db: AsyncSession,
        order_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Order]:
        """Get order by ID, optionally filtered by user"""
        query = select(Order).where(Order.id == order_id)
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if order:
            # Load items
            items_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order.items = list(items_result.scalars().all())
        
        return order

    @staticmethod
    async def get_order_by_number(
        db: AsyncSession,
        order_number: str,
        user_id: Optional[int] = None
    ) -> Optional[Order]:
        """Get order by order number"""
        query = select(Order).where(Order.order_number == order_number)
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if order:
            # Load items
            items_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order.items = list(items_result.scalars().all())
        
        return order

    @staticmethod
    async def get_user_orders(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[OrderStatus] = None
    ) -> Tuple[List[Order], int]:
        """Get user's orders with pagination"""
        query = select(Order).where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        
        # Count total
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        orders = list(result.scalars().all())
        
        # Load items for each order
        for order in orders:
            items_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order.items = list(items_result.scalars().all())
        
        return orders, total

    @staticmethod
    async def complete_order(
        db: AsyncSession,
        order: Order,
        transaction: Transaction
    ) -> bool:
        """
        Complete order after successful payment
        - Update order status
        - Distribute funds to shops
        - Clear cart
        - Update product stats
        """
        try:
            # Load order items if not loaded
            if not order.items:
                items_result = await db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id)
                )
                order.items = list(items_result.scalars().all())
            
            # Get commission rate
            from app.services.settings_service import settings_service
            commission_rate = await settings_service.get_setting_float(
                db, "shop_commission_rate", 10.0
            )
            
            # Process each item
            for item in order.items:
                # Update product stats
                product_result = await db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = product_result.scalar_one_or_none()
                if product:
                    product.purchases_count = (product.purchases_count or 0) + item.quantity
                
                # Calculate shop amount after commission
                commission_amount = item.subtotal * (commission_rate / 100)
                shop_amount = item.subtotal - commission_amount
                
                # Create commission transaction
                commission_tx = Transaction(
                    shop_id=item.shop_id,
                    type=TransactionType.COMMISSION,
                    amount=commission_amount,
                    status=TransactionStatus.COMPLETED,
                    extra_data={
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "product_id": item.product_id,
                        "commission_rate": commission_rate,
                        "shop_amount": float(shop_amount)
                    }
                )
                db.add(commission_tx)
                
                # Update shop balance (credit shop_amount)
                shop_result = await db.execute(
                    select(Shop).where(Shop.id == item.shop_id)
                )
                shop = shop_result.scalar_one_or_none()
                if shop:
                    shop.balance = float(shop.balance) + shop_amount
                    logger.info(f"Credited shop {shop.id} with ${shop_amount:.2f} for order {order.order_number}")
            
            # Update order status
            order.status = OrderStatus.COMPLETED
            order.transaction_id = transaction.id
            
            # Clear user's cart
            await cart_service.clear_cart(db, order.user_id)
            
            await db.commit()
            
            logger.info(f"Order {order.order_number} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error completing order {order.id}: {e}", exc_info=True)
            await db.rollback()
            return False


order_service = OrderService()
