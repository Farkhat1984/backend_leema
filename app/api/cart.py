"""Cart API endpoints for Flutter mobile app"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.shop import Shop
from app.services.cart_service import cart_service
from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartResponse,
    ProductInCart
)
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/items", response_model=CartItemResponse)
async def add_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add product to cart (Flutter mobile app)
    If product already in cart, quantity will be increased
    """
    cart_item, error = await cart_service.add_item(
        db,
        current_user.id,
        item_data.product_id,
        item_data.quantity
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Load product details for response
    from app.models.product import Product
    product_result = await db.execute(
        select(Product).where(Product.id == cart_item.product_id)
    )
    product = product_result.scalar_one_or_none()
    
    # Load shop name
    shop_name = None
    if product:
        shop_result = await db.execute(
            select(Shop).where(Shop.id == product.shop_id)
        )
        shop = shop_result.scalar_one_or_none()
        if shop:
            shop_name = shop.shop_name
    
    # Build response
    response = CartItemResponse.model_validate(cart_item)
    if product:
        response.product = ProductInCart(
            id=product.id,
            name=product.name,
            price=float(product.price),
            images=product.images,
            shop_id=product.shop_id,
            shop_name=shop_name,
            is_active=product.is_active
        )
        response.subtotal = float(product.price) * cart_item.quantity
    
    logger.info(f"[CART] User {current_user.id} added product {item_data.product_id} to cart")
    return response


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's cart with all items (Flutter mobile app)"""
    cart = await cart_service.get_cart_with_items(db, current_user.id)
    
    if not cart:
        # Return empty cart
        return CartResponse(
            id=0,
            user_id=current_user.id,
            items=[],
            total_items=0,
            total_price=0.0,
            created_at=None,
            updated_at=None
        )
    
    # Build response with product details
    items_response = []
    total_price = 0.0
    total_items = 0
    
    for item in cart.items:
        # Load shop name
        shop_name = None
        if item.product:
            shop_result = await db.execute(
                select(Shop).where(Shop.id == item.product.shop_id)
            )
            shop = shop_result.scalar_one_or_none()
            if shop:
                shop_name = shop.shop_name
            
            # Build item response
            item_response = CartItemResponse.model_validate(item)
            item_response.product = ProductInCart(
                id=item.product.id,
                name=item.product.name,
                price=float(item.product.price),
                images=item.product.images,
                shop_id=item.product.shop_id,
                shop_name=shop_name,
                is_active=item.product.is_active
            )
            item_response.subtotal = float(item.product.price) * item.quantity
            items_response.append(item_response)
            
            # Calculate totals
            if item.product.is_active:
                total_price += float(item.product.price) * item.quantity
                total_items += item.quantity
    
    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        items=items_response,
        total_items=total_items,
        total_price=total_price,
        created_at=cart.created_at,
        updated_at=cart.updated_at
    )


@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update cart item quantity (Flutter mobile app)"""
    cart_item, error = await cart_service.update_item_quantity(
        db,
        current_user.id,
        item_id,
        item_data.quantity
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Load product details
    from app.models.product import Product
    product_result = await db.execute(
        select(Product).where(Product.id == cart_item.product_id)
    )
    product = product_result.scalar_one_or_none()
    
    # Load shop name
    shop_name = None
    if product:
        shop_result = await db.execute(
            select(Shop).where(Shop.id == product.shop_id)
        )
        shop = shop_result.scalar_one_or_none()
        if shop:
            shop_name = shop.shop_name
    
    # Build response
    response = CartItemResponse.model_validate(cart_item)
    if product:
        response.product = ProductInCart(
            id=product.id,
            name=product.name,
            price=float(product.price),
            images=product.images,
            shop_id=product.shop_id,
            shop_name=shop_name,
            is_active=product.is_active
        )
        response.subtotal = float(product.price) * cart_item.quantity
    
    logger.info(f"[CART] User {current_user.id} updated cart item {item_id} quantity to {item_data.quantity}")
    return response


@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove item from cart (Flutter mobile app)"""
    success, error = await cart_service.remove_item(
        db,
        current_user.id,
        item_id
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    logger.info(f"[CART] User {current_user.id} removed cart item {item_id}")
    return {"message": "Item removed from cart successfully"}


@router.delete("")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear all items from cart (Flutter mobile app)"""
    success, error = await cart_service.clear_cart(db, current_user.id)
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    logger.info(f"[CART] User {current_user.id} cleared cart")
    return {"message": "Cart cleared successfully"}
