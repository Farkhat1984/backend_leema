from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.core.paypal import paypal_client
from app.services.user_service import user_service
from app.services.product_service import product_service
from app.services.settings_service import settings_service
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """Payment processing service"""

    @staticmethod
    async def create_top_up_payment(
        db: AsyncSession,
        user_id: int,
        amount: float,
        platform: str = "web"
    ) -> Optional[Dict]:
        """Create PayPal payment for user balance top-up"""
        user = await user_service.get_by_id(db, user_id)
        if not user:
            return None

        # Create PayPal order
        order = await paypal_client.create_order(
            amount=amount,
            description=f"Balance top-up for {user.email}",
            platform=platform
        )
        if not order:
            return None

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.TOP_UP,
            amount=amount,
            paypal_order_id=order["order_id"],
            status=TransactionStatus.PENDING,
            extra_data={"description": "Balance top-up"}
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        logger.info(f"Top-up payment created for user {user_id}: {amount}")
        return {
            "transaction_id": transaction.id,
            "order_id": order["order_id"],
            "approval_url": order["approval_url"],
            "amount": amount,
        }

    @staticmethod
    async def create_shop_top_up_payment(
        db: AsyncSession,
        shop_id: int,
        amount: float,
        platform: str = "web"
    ) -> Optional[Dict]:
        """Create PayPal payment for shop balance top-up"""
        from app.services.shop_service import shop_service

        shop = await shop_service.get_by_id(db, shop_id)
        if not shop:
            return None

        # Create PayPal order
        order = await paypal_client.create_order(
            amount=amount,
            description=f"Balance top-up for shop {shop.shop_name}",
            platform=platform
        )
        if not order:
            return None

        # Create transaction record
        transaction = Transaction(
            shop_id=shop_id,
            type=TransactionType.TOP_UP,
            amount=amount,
            paypal_order_id=order["order_id"],
            status=TransactionStatus.PENDING,
            extra_data={"description": "Shop balance top-up"}
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        logger.info(f"Top-up payment created for shop {shop_id}: {amount}")
        return {
            "transaction_id": transaction.id,
            "order_id": order["order_id"],
            "approval_url": order["approval_url"],
            "amount": amount,
        }

    @staticmethod
    async def create_rent_payment(
        db: AsyncSession,
        shop_id: int,
        product_id: int,
        months: int,
        platform: str = "web"
    ) -> Optional[Dict]:
        """Create PayPal payment for product rent"""
        from app.services.shop_service import shop_service

        shop = await shop_service.get_by_id(db, shop_id)
        if not shop:
            return None

        product = await product_service.get_by_id(db, product_id)
        if not product or product.shop_id != shop_id:
            return None

        # Calculate rent amount
        rent_price = await settings_service.get_setting_float(
            db, "shop_product_rent_price", 10.0
        )
        min_months = await settings_service.get_setting_int(
            db, "shop_min_rent_months", 1
        )

        if months < min_months:
            months = min_months

        total_amount = rent_price * months

        # Create PayPal order
        order = await paypal_client.create_order(
            amount=total_amount,
            description=f"Product rent for {months} months - {product.name}",
            platform=platform
        )
        if not order:
            return None

        # Create transaction record
        transaction = Transaction(
            shop_id=shop_id,
            type=TransactionType.PRODUCT_RENT,
            amount=total_amount,
            paypal_order_id=order["order_id"],
            status=TransactionStatus.PENDING,
            extra_data={
                "product_id": product_id,
                "months": months,
                "description": f"Product rent for {months} months"
            }
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        logger.info(f"Rent payment created for shop {shop_id}, product {product_id}: {total_amount}")
        return {
            "transaction_id": transaction.id,
            "order_id": order["order_id"],
            "approval_url": order["approval_url"],
            "amount": total_amount,
            "months": months,
        }

    @staticmethod
    async def capture_payment(
        db: AsyncSession,
        order_id: str
    ) -> Optional[Transaction]:
        """Capture PayPal payment and update transaction"""
        # Get transaction by order_id
        from sqlalchemy import select
        result = await db.execute(
            select(Transaction).where(Transaction.paypal_order_id == order_id)
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            logger.error(f"Transaction not found for order {order_id}")
            return None

        # Capture PayPal order
        capture = await paypal_client.capture_order(order_id)
        if not capture:
            transaction.status = TransactionStatus.FAILED
            await db.commit()
            return None

        # Update transaction
        transaction.paypal_capture_id = capture["capture_id"]
        transaction.status = TransactionStatus.COMPLETED

        # Process based on transaction type
        if transaction.type == TransactionType.TOP_UP:
            # Add balance to user or shop
            if transaction.user_id:
                await user_service.add_balance(db, transaction.user_id, float(transaction.amount))
            elif transaction.shop_id:
                from app.services.shop_service import shop_service
                await shop_service.add_balance(db, transaction.shop_id, float(transaction.amount))

        elif transaction.type == TransactionType.PRODUCT_RENT:
            # Activate product rent
            product_id = transaction.extra_data.get("product_id")
            months = transaction.extra_data.get("months", 1)
            if product_id:
                await product_service.set_rent_period(db, product_id, months)

        await db.commit()
        await db.refresh(transaction)
        logger.info(f"Payment captured: {order_id}")
        return transaction

    @staticmethod
    async def create_order_payment_from_cart(
        db: AsyncSession,
        user_id: int,
        platform: str = "mobile"
    ) -> Optional[Dict]:
        """
        Create PayPal payment for order from cart
        Returns: {order_id, order_number, approval_url, amount}
        """
        from app.services.cart_service import cart_service
        from app.services.order_service import order_service
        
        # Get cart with items
        cart = await cart_service.get_cart_with_items(db, user_id)
        if not cart or not cart.items:
            logger.warning(f"User {user_id} tried to create order from empty cart")
            return None
        
        # Create order from cart
        order, error = await order_service.create_order_from_cart(db, user_id, cart)
        if error or not order:
            logger.error(f"Failed to create order from cart for user {user_id}: {error}")
            return None
        
        # Create PayPal order
        paypal_order = await paypal_client.create_order(
            amount=float(order.total_amount),
            description=f"Order {order.order_number}",
            platform=platform
        )
        if not paypal_order:
            logger.error(f"Failed to create PayPal order for {order.order_number}")
            return None
        
        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.PRODUCT_PURCHASE,
            amount=float(order.total_amount),
            paypal_order_id=paypal_order["order_id"],
            status=TransactionStatus.PENDING,
            extra_data={
                "order_id": order.id,
                "order_number": order.order_number,
                "items_count": len(order.items),
                "description": f"Order {order.order_number}"
            }
        )
        db.add(transaction)
        
        # Link transaction to order
        order.transaction_id = transaction.id
        
        await db.commit()
        await db.refresh(transaction)
        await db.refresh(order)
        
        logger.info(f"Created payment for order {order.order_number}: ${order.total_amount:.2f}")
        return {
            "transaction_id": transaction.id,
            "order_id": order.id,
            "order_number": order.order_number,
            "approval_url": paypal_order["approval_url"],
            "amount": float(order.total_amount),
        }

    @staticmethod
    async def process_product_purchase(
        db: AsyncSession,
        user_id: int,
        product_id: int,
        platform: str = "web"
    ) -> Optional[Dict]:
        """Process product purchase (creates PayPal payment) - LEGACY for single product"""
        user = await user_service.get_by_id(db, user_id)
        product = await product_service.get_by_id(db, product_id)

        if not user or not product or not product.is_active:
            return None

        amount = float(product.price)

        # Create PayPal order
        order = await paypal_client.create_order(
            amount=amount,
            description=f"Purchase: {product.name}",
            platform=platform
        )
        if not order:
            return None

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.PRODUCT_PURCHASE,
            amount=amount,
            paypal_order_id=order["order_id"],
            status=TransactionStatus.PENDING,
            extra_data={
                "product_id": product_id,
                "shop_id": product.shop_id,
                "description": f"Purchase: {product.name}"
            }
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        logger.info(f"Purchase payment created for user {user_id}, product {product_id}: {amount}")
        return {
            "transaction_id": transaction.id,
            "order_id": order["order_id"],
            "approval_url": order["approval_url"],
            "amount": amount,
        }

    @staticmethod
    async def complete_product_purchase(
        db: AsyncSession,
        transaction: Transaction
    ) -> bool:
        """Complete product purchase after payment capture"""
        if transaction.type != TransactionType.PRODUCT_PURCHASE:
            return False

        # Check if this is an order (new flow) or single product (legacy)
        order_id = transaction.extra_data.get("order_id")
        
        if order_id:
            # New flow: Complete full order
            from app.services.order_service import order_service
            from app.models.order import Order
            
            order_result = await db.execute(
                select(Order).where(Order.id == order_id)
            )
            order = order_result.scalar_one_or_none()
            
            if order:
                return await order_service.complete_order(db, order, transaction)
            
            logger.error(f"Order {order_id} not found for transaction {transaction.id}")
            return False
        
        # Legacy flow: Single product purchase
        product_id = transaction.extra_data.get("product_id")
        shop_id = transaction.extra_data.get("shop_id")

        if not product_id or not shop_id:
            return False

        # Increment purchase count
        await product_service.increment_purchases(db, product_id)

        # Calculate commission
        commission_rate = await settings_service.get_setting_float(
            db, "shop_commission_rate", 10.0
        )
        commission_amount = float(transaction.amount) * (commission_rate / 100)
        shop_amount = float(transaction.amount) - commission_amount

        # Create commission transaction for platform
        commission_tx = Transaction(
            shop_id=shop_id,
            type=TransactionType.COMMISSION,
            amount=commission_amount,
            status=TransactionStatus.COMPLETED,
            extra_data={
                "product_id": product_id,
                "original_transaction_id": transaction.id,
                "commission_rate": commission_rate
            }
        )
        db.add(commission_tx)

        # Note: In production, you would transfer shop_amount to shop's account
        # For MVP, we just log it
        logger.info(f"Product purchase completed: {product_id}, commission: {commission_amount}, shop_amount: {shop_amount}")

        await db.commit()
        return True


payment_service = PaymentService()
