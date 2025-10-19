"""Orders API endpoints for Flutter mobile app"""
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.shop import Shop
from app.models.refund import Refund
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
    Supports PayPal and Balance payment methods
    """
    user_id = current_user.id  # Store user_id to avoid detached instance errors
    try:
        logger.info(f"[ORDER] Creating order from cart for user {user_id}, payment_method: {order_data.payment_method}")
        
        # Validate cart is not empty
        from app.services.cart_service import cart_service
        cart = await cart_service.get_cart_with_items(db, user_id)
        if not cart or not cart.items:
            logger.warning(f"[ORDER] User {user_id} attempted checkout with empty cart")
            raise HTTPException(
                status_code=400,
                detail="Your cart is empty. Please add items before checkout."
            )
        
        platform = "mobile" if x_client_platform == "mobile" else "web"
        
        if order_data.payment_method == "paypal":
            # Create order and PayPal payment
            try:
                logger.info(f"[ORDER] Creating PayPal payment for user {user_id}")
                payment_result = await payment_service.create_order_payment_from_cart(
                    db, user_id, platform=platform, payment_method="paypal"
                )
                
                if not payment_result:
                    logger.error(f"[ORDER] PayPal payment creation failed for user {user_id}")
                    raise HTTPException(
                        status_code=500,
                        detail="PayPal payment gateway is temporarily unavailable. Please try again later or use another payment method."
                    )
                
                logger.info(f"[ORDER] Successfully created PayPal order {payment_result['order_number']} for user {user_id}")
                
                return {
                    "order_id": payment_result["order_id"],
                    "order_number": payment_result["order_number"],
                    "approval_url": payment_result["approval_url"],
                    "amount": payment_result["amount"],
                    "payment_method": "paypal",
                    "status": payment_result.get("status", "pending")
                }
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[ORDER] PayPal order creation error for user {user_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create PayPal payment. Please try again or use another payment method."
                )
        
        elif order_data.payment_method == "balance":
            # Check balance first
            from app.services.user_service import user_service
            user = await user_service.get_by_id(db, user_id)
            if not user:
                logger.error(f"[ORDER] User {user_id} not found")
                raise HTTPException(status_code=404, detail="User not found")
            
            # Calculate cart total
            cart_total = sum(float(item.product.price) * item.quantity for item in cart.items if item.product)
            user_balance = float(user.balance)  # Convert Decimal to float
            
            if user_balance < cart_total:
                logger.warning(f"[ORDER] User {user_id} has insufficient balance: {user_balance} < {cart_total}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "insufficient_balance",
                        "message": f"Insufficient balance. You have ${user_balance:.2f}, but need ${cart_total:.2f}",
                        "current_balance": user_balance,
                        "required_amount": cart_total,
                        "shortfall": cart_total - user_balance
                    }
                )
            
            # Create order and pay with balance
            try:
                logger.info(f"[ORDER] Creating balance payment for user {user_id}")
                payment_result = await payment_service.create_order_payment_from_cart(
                    db, user_id, platform=platform, payment_method="balance"
                )
                
                if not payment_result:
                    logger.error(f"[ORDER] Balance payment creation failed for user {user_id}")
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to process payment with balance. Please try again."
                    )
                
                # TODO: Send WebSocket notification for completed order
                # Currently disabled due to schema mismatch
                # from app.core.websocket import connection_manager
                # from app.schemas.webhook import create_order_event, WebhookEventType
                
                logger.info(f"[ORDER] Successfully created and completed balance order {payment_result['order_number']} for user {user_id}")
                
                # Get updated user balance
                await db.refresh(user)
                
                return {
                    "order_id": payment_result["order_id"],
                    "order_number": payment_result["order_number"],
                    "amount": payment_result["amount"],
                    "payment_method": "balance",
                    "status": "completed",
                    "message": "Order paid successfully with your balance",
                    "new_balance": float(user.balance)
                }
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[ORDER] Balance payment error for user {user_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to process payment with balance. Please try again."
                )
        
        else:
            logger.warning(f"[ORDER] Invalid payment method '{order_data.payment_method}' from user {user_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payment method: {order_data.payment_method}. Supported methods: paypal, balance"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ORDER] Unexpected error in create_order_from_cart for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating your order. Please try again later."
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get order details by ID (Flutter mobile app)"""
    user_id = current_user.id
    order = await order_service.get_order_by_id(db, order_id, user_id)
    
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
        db, user_id, skip, limit, status_enum
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


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel order (Flutter mobile app)
    Only PENDING orders can be cancelled
    Refunds amount to user balance
    """
    user_id = current_user.id
    order = await order_service.get_order_by_id(db, order_id, user_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if can cancel
    can_cancel, error = await order_service.can_cancel_order(order)
    if not can_cancel:
        raise HTTPException(status_code=400, detail=error)
    
    # Cancel order
    success, error = await order_service.cancel_order(db, order, user_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    # Send WebSocket notifications
    from app.core.websocket import connection_manager
    from app.schemas.webhook import create_order_event, WebhookEventType
    
    # Notify user
    order_event = create_order_event(
        event_type=WebhookEventType.ORDER_CANCELLED,
        order_id=order.id,
        order_number=order.order_number,
        user_id=user_id,
        total_amount=float(order.total_amount),
        status="cancelled"
    )
    await connection_manager.send_to_client(order_event.model_dump(mode='json'), "user", user_id)
    
    # Notify shops (for each item)
    notified_shops = set()
    for item in order.items:
        if item.shop_id not in notified_shops:
            await connection_manager.send_to_client(order_event.model_dump(mode='json'), "shop", item.shop_id)
            notified_shops.add(item.shop_id)
    
    # Notify admins
    await connection_manager.broadcast_to_type(order_event.model_dump(mode='json'), "admin")
    
    logger.info(f"[ORDER] Order {order.order_number} cancelled by user {user_id}")
    
    return {
        "message": "Order cancelled successfully",
        "order_id": order.id,
        "order_number": order.order_number,
        "refunded_amount": float(order.total_amount),
        "status": "cancelled"
    }


@router.post("/{order_id}/refund")
async def request_order_refund(
    order_id: int,
    reason: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request refund for completed order (Flutter mobile app)
    Creates refund request for admin approval
    """
    if not reason or len(reason.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Please provide a detailed reason (at least 10 characters)"
        )
    
    user_id = current_user.id
    order = await order_service.get_order_by_id(db, order_id, user_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Request refund
    success, error = await order_service.request_refund(db, order, user_id, reason)
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    # Send WebSocket notifications
    from app.core.websocket import connection_manager
    from app.schemas.webhook import create_refund_event, WebhookEventType
    
    # Get refund ID
    from app.models.refund import Refund
    refund_result = await db.execute(
        select(Refund).where(Refund.transaction_id == order.transaction_id)
    )
    refund = refund_result.scalar_one_or_none()
    
    if refund:
        refund_event = create_refund_event(
            event_type=WebhookEventType.REFUND_REQUESTED,
            refund_id=refund.id,
            order_id=order.id,
            order_number=order.order_number,
            user_id=user_id,
            amount=float(order.total_amount),
            reason=reason,
            status="requested"
        )
        
        # Notify user
        await connection_manager.send_to_client(refund_event.model_dump(mode='json'), "user", user_id)
        
        # Notify admins
        await connection_manager.broadcast_to_type(refund_event.model_dump(mode='json'), "admin")
    
    logger.info(f"[REFUND] Refund requested for order {order.order_number} by user {user_id}")
    
    return {
        "message": "Refund request submitted successfully",
        "order_id": order.id,
        "order_number": order.order_number,
        "refund_id": refund.id if refund else None,
        "status": "requested",
        "note": "Your refund request will be reviewed by our team"
    }
