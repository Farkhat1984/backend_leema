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
