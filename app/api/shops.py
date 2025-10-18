from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_shop
from app.models.shop import Shop
from app.services.shop_service import shop_service
from app.schemas.shop import ShopResponse, ShopUpdate, ShopAnalytics
from app.schemas.product import ProductResponse
from app.schemas.transaction import TransactionResponse
from typing import List

router = APIRouter()


@router.get("/me", response_model=ShopResponse)
async def get_current_shop_info(
    current_shop: Shop = Depends(get_current_shop)
):
    """Get current shop information"""
    return ShopResponse.model_validate(current_shop)


@router.put("/me", response_model=ShopResponse)
async def update_current_shop(
    shop_data: ShopUpdate,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Update current shop"""
    updated_shop = await shop_service.update(db, current_shop.id, shop_data)
    if not updated_shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return ShopResponse.model_validate(updated_shop)


@router.get("/me/products", response_model=List[ProductResponse])
async def get_shop_products(
    skip: int = 0,
    limit: int = 50,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Get shop products"""
    products = await shop_service.get_products(db, current_shop.id, skip, limit)
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/me/analytics", response_model=ShopAnalytics)
async def get_shop_analytics(
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Get shop analytics"""
    return await shop_service.get_analytics(db, current_shop.id)


@router.get("/me/transactions", response_model=List[TransactionResponse])
async def get_shop_transactions(
    skip: int = 0,
    limit: int = 50,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Get shop transaction history"""
    try:
        transactions = await shop_service.get_transactions(db, current_shop.id, skip, limit)
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")


@router.get("/me/orders")
async def get_shop_orders(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Get shop orders - orders containing this shop's products (Web shop panel)"""
    from app.models.order import Order, OrderItem, OrderStatus
    from app.models.product import Product
    from app.models.user import User
    from app.schemas.order import OrderResponse, OrderItemResponse
    from sqlalchemy import select, func
    
    # Query orders that have items from this shop
    query = select(Order).join(OrderItem).where(OrderItem.shop_id == current_shop.id)
    
    # Filter by status
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.where(Order.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in OrderStatus]}"
            )
    
    # Count total
    count_query = select(func.count(Order.id.distinct())).select_from(
        Order.__table__.join(OrderItem.__table__)
    ).where(OrderItem.shop_id == current_shop.id)
    
    if status:
        count_query = count_query.where(Order.status == status_enum)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results (distinct orders)
    query = query.distinct().order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # Build response
    orders_response = []
    for order in orders:
        # Load ALL items (not just shop's items - for context)
        all_items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        all_items = list(all_items_result.scalars().all())
        
        # Filter items belonging to this shop
        shop_items = [item for item in all_items if item.shop_id == current_shop.id]
        
        response = OrderResponse.model_validate(order)
        
        # Load item details (only for shop's items)
        items_response = []
        shop_total = 0.0
        
        for item in shop_items:
            product_result = await db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = product_result.scalar_one_or_none()
            
            item_response = OrderItemResponse.model_validate(item)
            if product:
                item_response.product_name = product.name
            item_response.shop_name = current_shop.shop_name
            
            items_response.append(item_response)
            shop_total += float(item.subtotal)
        
        response.items = items_response
        
        # Add shop-specific total
        response.total_amount = shop_total
        
        orders_response.append(response)
    
    return {
        "orders": orders_response,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "note": "Shows only items from your shop"
    }


@router.get("/me/orders/{order_id}")
async def get_shop_order_details(
    order_id: int,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Get order details for shop (Web shop panel)"""
    from app.models.order import Order, OrderItem
    from app.models.product import Product
    from app.models.user import User
    from app.schemas.order import OrderResponse, OrderItemResponse
    
    order_result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = order_result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order contains shop's products
    shop_items_result = await db.execute(
        select(OrderItem).where(
            OrderItem.order_id == order_id,
            OrderItem.shop_id == current_shop.id
        )
    )
    shop_items = list(shop_items_result.scalars().all())
    
    if not shop_items:
        raise HTTPException(
            status_code=404,
            detail="No items from your shop in this order"
        )
    
    # Build response
    response = OrderResponse.model_validate(order)
    
    items_response = []
    shop_total = 0.0
    
    for item in shop_items:
        product_result = await db.execute(
            select(Product).where(Product.id == item.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        item_response = OrderItemResponse.model_validate(item)
        if product:
            item_response.product_name = product.name
        item_response.shop_name = current_shop.shop_name
        
        items_response.append(item_response)
        shop_total += float(item.subtotal)
    
    response.items = items_response
    response.total_amount = shop_total
    
    # Add user info
    user_result = await db.execute(
        select(User).where(User.id == order.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    return {
        "order": response,
        "shop_total": shop_total,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        } if user else None,
        "note": "Shows only items from your shop"
    }
