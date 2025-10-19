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
        cart: Cart,
        payment_method: str = "paypal"
    ) -> Tuple[Optional[Order], Optional[str]]:
        """
        Create order from cart items
        Returns: (Order, error_message)
        """
        if not cart or not cart.items:
            return None, "Cart is empty"
        
        # Validate payment method
        if payment_method not in ["paypal", "balance"]:
            return None, f"Invalid payment method: {payment_method}"
        
        # Validate all products are still available
        total_amount = 0.0
        for cart_item in cart.items:
            product = cart_item.product
            if not product or not product.is_active:
                return None, f"Product {cart_item.product_id} is no longer available"
            
            total_amount += float(product.price) * cart_item.quantity
        
        # Generate order number
        order_number = Order.generate_order_number()
        
        # Create order - use exact enum values from database
        order = Order(
            order_number=order_number,
            user_id=user_id,
            order_type="PURCHASE",  # Database has uppercase
            status="PENDING",  # Database has uppercase
            payment_method=payment_method,  # Database has lowercase (paypal/balance)
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
        
        logger.info(f"Created order {order_number} from cart for user {user_id}, total: ${total_amount:.2f}, payment: {payment_method}")
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
        order_id: int,
        transaction_id: int
    ) -> bool:
        """
        Complete order after successful payment
        - Update order status
        - Distribute funds to shops
        - Clear cart
        - Update product stats
        
        Best practice: Accept IDs to avoid detached instance issues
        """
        try:
            # Fetch order with eager loading
            from sqlalchemy.orm import selectinload
            
            order_result = await db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.id == order_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            # Save values before any modifications
            order_number = order.order_number
            user_id = order.user_id
            
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
                
                # Calculate shop amount after commission (convert to float early)
                item_subtotal = float(item.subtotal)
                commission_amount = item_subtotal * (commission_rate / 100)
                shop_amount = item_subtotal - commission_amount
                
                # Create commission transaction
                commission_tx = Transaction(
                    shop_id=item.shop_id,
                    type=TransactionType.COMMISSION,
                    amount=commission_amount,
                    status=TransactionStatus.COMPLETED,
                    extra_data={
                        "order_id": order_id,
                        "order_number": order_number,
                        "product_id": item.product_id,
                        "commission_rate": commission_rate,
                        "shop_amount": shop_amount
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
                    logger.info(f"Credited shop {shop.id} with ${shop_amount:.2f} for order {order_number}")
            
            # Update order status
            order.status = "COMPLETED"
            order.transaction_id = transaction_id
            
            # Clear user's cart
            await cart_service.clear_cart(db, user_id)
            
            # Don't commit here - let the caller commit
            # await db.commit()
            
            logger.info(f"Order {order_number} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error completing order {order_id or 'unknown'}: {e}", exc_info=True)
            # Don't rollback here - let the caller handle it
            # await db.rollback()
            return False

    @staticmethod
    async def can_cancel_order(order: Order) -> Tuple[bool, Optional[str]]:
        """
        Check if order can be cancelled
        Returns: (can_cancel, reason)
        """
        if order.status == OrderStatus.CANCELLED:
            return False, "Order is already cancelled"
        
        if order.status == OrderStatus.REFUNDED:
            return False, "Order has been refunded, cannot cancel"
        
        if order.status == OrderStatus.COMPLETED:
            return False, "Completed orders cannot be cancelled. Please request a refund instead."
        
        if order.status == OrderStatus.PENDING:
            return True, None
        
        return False, f"Cannot cancel order with status: {order.status.value}"

    @staticmethod
    async def cancel_order(
        db: AsyncSession,
        order: Order,
        user_id: int,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Cancel order and refund to user balance
        Only for PENDING orders
        """
        # Verify ownership
        if order.user_id != user_id:
            return False, "Order does not belong to this user"
        
        # Check if can cancel
        can_cancel, error = await OrderService.can_cancel_order(order)
        if not can_cancel:
            return False, error
        
        try:
            from app.models.user import User
            
            # Get user
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                return False, "User not found"
            
            # Refund amount to user balance
            old_balance = float(user.balance)
            user.balance = old_balance + float(order.total_amount)
            
            # Create refund transaction
            refund_transaction = Transaction(
                user_id=user_id,
                type=TransactionType.REFUND,
                amount=float(order.total_amount),
                status=TransactionStatus.COMPLETED,
                extra_data={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "reason": reason or "Order cancelled by user",
                    "original_amount": float(order.total_amount)
                }
            )
            db.add(refund_transaction)
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            
            await db.commit()
            
            logger.info(
                f"Order {order.order_number} cancelled by user {user_id}. "
                f"Refunded ${order.total_amount:.2f} to balance"
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error cancelling order {order.id}: {e}", exc_info=True)
            await db.rollback()
            return False, f"Failed to cancel order: {str(e)}"

    @staticmethod
    async def request_refund(
        db: AsyncSession,
        order: Order,
        user_id: int,
        reason: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Request refund for completed order
        Creates Refund request for admin approval
        """
        from app.models.refund import Refund, RefundStatus
        
        # Verify ownership
        if order.user_id != user_id:
            return False, "Order does not belong to this user"
        
        # Check order status
        if order.status != OrderStatus.COMPLETED:
            return False, "Only completed orders can be refunded"
        
        if order.status == OrderStatus.REFUNDED:
            return False, "Order has already been refunded"
        
        if order.status == OrderStatus.CANCELLED:
            return False, "Cancelled orders cannot be refunded"
        
        # Check if refund already exists
        if order.transaction_id:
            existing_refund_result = await db.execute(
                select(Refund).where(Refund.transaction_id == order.transaction_id)
            )
            existing_refund = existing_refund_result.scalar_one_or_none()
            
            if existing_refund:
                return False, f"Refund already exists with status: {existing_refund.status.value}"
        
        try:
            # Create refund request
            refund = Refund(
                transaction_id=order.transaction_id,
                user_id=user_id,
                reason=reason,
                status=RefundStatus.REQUESTED
            )
            db.add(refund)
            
            # Update order status to indicate refund requested
            order.status = OrderStatus.REFUNDED
            
            await db.commit()
            await db.refresh(refund)
            
            logger.info(
                f"Refund request created for order {order.order_number} "
                f"by user {user_id}. Refund ID: {refund.id}"
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error creating refund request for order {order.id}: {e}", exc_info=True)
            await db.rollback()
            return False, f"Failed to create refund request: {str(e)}"


order_service = OrderService()
