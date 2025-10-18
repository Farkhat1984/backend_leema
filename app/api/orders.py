"""Orders API endpoints for Flutter mobile app"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.shop import Shop
from app.services.order_service import order_service
from app.services.payment_service import payment_service
from app.schemas.order import (
    OrderCreateFromCart,
    OrderResponse,
    OrderListResponse,
    OrderItemResponse
)
from app.schemas.payment import PaymentResponse
from typing import List, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create-from-cart", response_model=dict)
async def create_order_from_cart(
    order_data: OrderCreateFromCart,
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create order from cart and initiate payment (Flutter mobile app)
    Supports PayPal payment (balance payment coming soon)
    """
    platform = "mobile" if x_client_platform == "mobile" else "web"
    
    if order_data.payment_method == "paypal":
        # Create order and PayPal payment
        payment_result = await payment_service.create_order_payment_from_cart(
            db, current_user.id, platform=platform
        )
        
        if not payment_result:
            raise HTTPException(status_code=400, detail="Failed to create order or payment")
        
        logger.info(f"[ORDER] Created order {payment_result['order_number']} for user {current_user.id}")
        
        return {
            "order_id": payment_result["order_id"],
            "order_number": payment_result["order_number"],
            "approval_url": payment_result["approval_url"],
            "amount": payment_result["amount"],
            "payment_method": "paypal",
            "status": "pending"
        }
    
    elif order_data.payment_method == "balance":
        # TODO: Implement balance payment in ЭТАП 5
        raise HTTPException(
            status_code=501,
            detail="Balance payment not implemented yet. Please use PayPal."
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid payment method")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get order details by ID (Flutter mobile app)"""
    order = await order_service.get_order_by_id(db, order_id, current_user.id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Build response with item details
    response = OrderResponse.model_validate(order)
    
    # Load product and shop details for each item
    items_response = []
    for item in order.items:
        product_result = await db.execute(
            select(Product).where(Product.id == item.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        shop_result = await db.execute(
            select(Shop).where(Shop.id == item.shop_id)
        )
        shop = shop_result.scalar_one_or_none()
        
        item_response = OrderItemResponse.model_validate(item)
        if product:
            item_response.product_name = product.name
        if shop:
            item_response.shop_name = shop.shop_name
        
        items_response.append(item_response)
    
    response.items = items_response
    
    return response


@router.get("", response_model=OrderListResponse)
async def get_user_orders(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's order history (Flutter mobile app)"""
    # Validate status
    status_enum = None
    if status:
        try:
            status_enum = OrderStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in OrderStatus]}"
            )
    
    orders, total = await order_service.get_user_orders(
        db, current_user.id, skip, limit, status_enum
    )
    
    # Build response with details
    orders_response = []
    for order in orders:
        response = OrderResponse.model_validate(order)
        
        # Load item details
        items_response = []
        for item in order.items:
            product_result = await db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = product_result.scalar_one_or_none()
            
            shop_result = await db.execute(
                select(Shop).where(Shop.id == item.shop_id)
            )
            shop = shop_result.scalar_one_or_none()
            
            item_response = OrderItemResponse.model_validate(item)
            if product:
                item_response.product_name = product.name
            if shop:
                item_response.shop_name = shop.shop_name
            
            items_response.append(item_response)
        
        response.items = items_response
        orders_response.append(response)
    
    return OrderListResponse(
        orders=orders_response,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )
