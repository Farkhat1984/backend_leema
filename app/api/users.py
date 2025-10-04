from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order
from app.services.user_service import user_service
from app.schemas.user import UserResponse, UserUpdate, UserBalance
from app.schemas.transaction import TransactionResponse
from app.schemas.generation import GenerationResponse
from app.schemas.order import OrderResponse
from typing import List

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user"""
    updated_user = await user_service.update(db, current_user.id, user_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(updated_user)


@router.get("/me/balance", response_model=UserBalance)
async def get_user_balance(
    current_user: User = Depends(get_current_user)
):
    """Get user balance and free limits"""
    return UserBalance(
        balance=float(current_user.balance),
        free_generations_left=current_user.free_generations_left,
        free_try_ons_left=current_user.free_try_ons_left
    )


@router.get("/me/transactions", response_model=List[TransactionResponse])
async def get_user_transactions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user transaction history"""
    transactions = await user_service.get_transactions(db, current_user.id, skip, limit)
    return [TransactionResponse.model_validate(t) for t in transactions]


@router.get("/me/history", response_model=List[GenerationResponse])
async def get_user_generation_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user generation/try-on history"""
    generations = await user_service.get_generations(db, current_user.id, skip, limit)
    return [GenerationResponse.model_validate(g) for g in generations]


@router.get("/me/orders", response_model=List[OrderResponse])
async def get_user_orders(
    skip: int = 0,
    limit: int = 50,
    order_type: str = None,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user purchase and rental history"""
    from app.models.order import OrderType, OrderStatus
    from app.models.product import Product
    from app.models.shop import Shop
    
    query = (
        select(Order)
        .join(Product, Order.product_id == Product.id)
        .join(Shop, Order.shop_id == Shop.id)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    
    if order_type:
        try:
            order_type_enum = OrderType(order_type)
            query = query.where(Order.order_type == order_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order_type. Must be one of: {[t.value for t in OrderType]}"
            )
    
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.where(Order.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in OrderStatus]}"
            )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # Enrich with product/shop info
    order_responses = []
    for order in orders:
        order_dict = OrderResponse.model_validate(order).model_dump()
        
        # Get product info
        product_result = await db.execute(select(Product).where(Product.id == order.product_id))
        product = product_result.scalar_one_or_none()
        if product:
            order_dict['product_name'] = product.name
            order_dict['product_price'] = float(product.price)
        
        # Get shop info
        shop_result = await db.execute(select(Shop).where(Shop.id == order.shop_id))
        shop = shop_result.scalar_one_or_none()
        if shop:
            order_dict['shop_name'] = shop.shop_name
        
        order_responses.append(OrderResponse(**order_dict))
    
    return order_responses
