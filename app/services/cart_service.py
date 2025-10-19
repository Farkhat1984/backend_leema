"""Cart service for shopping cart operations"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.shop import Shop
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CartService:
    """Service for managing shopping cart operations"""

    @staticmethod
    async def get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
        """Get existing cart or create new one for user"""
        result = await db.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()
        
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
            logger.info(f"Created new cart for user {user_id}")
        
        return cart

    @staticmethod
    async def get_cart_with_items(db: AsyncSession, user_id: int) -> Optional[Cart]:
        """Get cart with all items and product details using proper eager loading"""
        try:
            # Use selectinload to eagerly load items and their products
            result = await db.execute(
                select(Cart)
                .where(Cart.user_id == user_id)
                .options(
                    selectinload(Cart.items).selectinload(CartItem.product)
                )
            )
            cart = result.scalar_one_or_none()
            
            if cart:
                logger.info(f"[CART] Loaded cart {cart.id} for user {user_id} with {len(cart.items)} items")
            else:
                logger.info(f"[CART] No cart found for user {user_id}")
            
            return cart
        except Exception as e:
            logger.error(f"[CART] Error getting cart with items for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    async def add_item(
        db: AsyncSession,
        user_id: int,
        product_id: int,
        quantity: int = 1
    ) -> Tuple[Optional[CartItem], Optional[str]]:
        """
        Add item to cart or update quantity if already exists
        Returns: (CartItem, error_message)
        """
        # Validate product
        product_result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            return None, "Product not found"
        
        if not product.is_active:
            return None, "Product is not available"
        
        # Get or create cart
        cart = await CartService.get_or_create_cart(db, user_id)
        
        # Check if item already in cart
        existing_item_result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id
            )
        )
        existing_item = existing_item_result.scalar_one_or_none()
        
        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
            await db.commit()
            await db.refresh(existing_item)
            logger.info(f"Updated cart item quantity: cart={cart.id}, product={product_id}, new_qty={existing_item.quantity}")
            return existing_item, None
        else:
            # Create new cart item
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity
            )
            db.add(cart_item)
            await db.commit()
            await db.refresh(cart_item)
            logger.info(f"Added item to cart: cart={cart.id}, product={product_id}, qty={quantity}")
            return cart_item, None

    @staticmethod
    async def update_item_quantity(
        db: AsyncSession,
        user_id: int,
        cart_item_id: int,
        quantity: int
    ) -> Tuple[Optional[CartItem], Optional[str]]:
        """Update cart item quantity"""
        # Get cart item
        item_result = await db.execute(
            select(CartItem).where(CartItem.id == cart_item_id)
        )
        item = item_result.scalar_one_or_none()
        
        if not item:
            return None, "Cart item not found"
        
        # Verify ownership
        cart_result = await db.execute(
            select(Cart).where(Cart.id == item.cart_id, Cart.user_id == user_id)
        )
        cart = cart_result.scalar_one_or_none()
        
        if not cart:
            return None, "Cart item does not belong to this user"
        
        # Update quantity
        item.quantity = quantity
        await db.commit()
        await db.refresh(item)
        logger.info(f"Updated cart item quantity: item={cart_item_id}, qty={quantity}")
        
        return item, None

    @staticmethod
    async def remove_item(
        db: AsyncSession,
        user_id: int,
        cart_item_id: int
    ) -> Tuple[bool, Optional[str]]:
        """Remove item from cart"""
        # Get cart item
        item_result = await db.execute(
            select(CartItem).where(CartItem.id == cart_item_id)
        )
        item = item_result.scalar_one_or_none()
        
        if not item:
            return False, "Cart item not found"
        
        # Verify ownership
        cart_result = await db.execute(
            select(Cart).where(Cart.id == item.cart_id, Cart.user_id == user_id)
        )
        cart = cart_result.scalar_one_or_none()
        
        if not cart:
            return False, "Cart item does not belong to this user"
        
        # Delete item
        await db.delete(item)
        await db.commit()
        logger.info(f"Removed cart item: item={cart_item_id}")
        
        return True, None

    @staticmethod
    async def clear_cart(db: AsyncSession, user_id: int) -> Tuple[bool, Optional[str]]:
        """Clear all items from cart"""
        cart_result = await db.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        cart = cart_result.scalar_one_or_none()
        
        if not cart:
            return False, "Cart not found"
        
        # Delete all items
        items_result = await db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )
        items = items_result.scalars().all()
        
        for item in items:
            await db.delete(item)
        
        await db.commit()
        logger.info(f"Cleared cart: cart={cart.id}, items_removed={len(items)}")
        
        return True, None

    @staticmethod
    async def get_cart_total(db: AsyncSession, cart: Cart) -> float:
        """Calculate total price of cart"""
        if not cart or not cart.items:
            return 0.0
        
        total = 0.0
        for item in cart.items:
            if item.product and item.product.is_active:
                total += float(item.product.price) * item.quantity
        
        return total

    @staticmethod
    async def get_cart_items_count(cart: Cart) -> int:
        """Get total number of items in cart"""
        if not cart or not cart.items:
            return 0
        
        return sum(item.quantity for item in cart.items)


cart_service = CartService()
