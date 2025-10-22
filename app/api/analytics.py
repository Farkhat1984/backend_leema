"""
Analytics endpoints - Track fashion trends and user behavior
Main purpose: Understand what people try on and save to wardrobe
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.wardrobe import UserWardrobeItem, WardrobeItemSource
from app.models.generation import Generation, GenerationType
from app.models.product import Product
from typing import List, Dict, Any
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/wardrobe/trends")
async def get_wardrobe_trends(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    🔥 АНАЛИТИКА: Что пользователи сохраняют в гардероб
    
    Показывает:
    - Какие товары из магазина чаще всего копируют
    - Какие характеристики популярны (цвет, размер, стиль)
    - Динамика по дням
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Топ товаров из магазина по добавлениям в гардероб
    query = (
        select(
            Product.id,
            Product.name,
            Product.characteristics,
            func.count(UserWardrobeItem.id).label("saves_count")
        )
        .join(UserWardrobeItem, UserWardrobeItem.original_product_id == Product.id)
        .where(
            and_(
                UserWardrobeItem.source == WardrobeItemSource.SHOP_PRODUCT,
                UserWardrobeItem.created_at >= since
            )
        )
        .group_by(Product.id, Product.name, Product.characteristics)
        .order_by(desc("saves_count"))
        .limit(limit)
    )
    
    result = await db.execute(query)
    top_products = result.all()
    
    # Распределение по источникам
    source_query = (
        select(
            UserWardrobeItem.source,
            func.count(UserWardrobeItem.id).label("count")
        )
        .where(UserWardrobeItem.created_at >= since)
        .group_by(UserWardrobeItem.source)
    )
    
    source_result = await db.execute(source_query)
    sources = source_result.all()
    
    # Динамика по дням
    daily_query = (
        select(
            func.date(UserWardrobeItem.created_at).label("date"),
            func.count(UserWardrobeItem.id).label("count")
        )
        .where(UserWardrobeItem.created_at >= since)
        .group_by(func.date(UserWardrobeItem.created_at))
        .order_by(func.date(UserWardrobeItem.created_at))
    )
    
    daily_result = await db.execute(daily_query)
    daily_stats = daily_result.all()
    
    return {
        "period_days": days,
        "top_saved_products": [
            {
                "product_id": p.id,
                "name": p.name,
                "saves_count": p.saves_count,
                "characteristics": p.characteristics
            }
            for p in top_products
        ],
        "by_source": [
            {"source": s.source, "count": s.count}
            for s in sources
        ],
        "daily_stats": [
            {"date": str(d.date), "count": d.count}
            for d in daily_stats
        ]
    }


@router.get("/try-on/trends")
async def get_try_on_trends(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    🔥 АНАЛИТИКА: Что пользователи примеряют
    
    Показывает:
    - Какие товары чаще всего примеряют
    - Conversion rate: примерка → сохранение в гардероб
    - Популярные категории для примерки
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Топ товаров по примеркам
    query = (
        select(
            Product.id,
            Product.name,
            Product.characteristics,
            func.count(Generation.id).label("try_on_count")
        )
        .join(Generation, Generation.product_id == Product.id)
        .where(
            and_(
                Generation.type == GenerationType.TRY_ON,
                Generation.created_at >= since
            )
        )
        .group_by(Product.id, Product.name, Product.characteristics)
        .order_by(desc("try_on_count"))
        .limit(limit)
    )
    
    result = await db.execute(query)
    top_tried = result.all()
    
    # Conversion rate: примерка → гардероб
    # Товары с примерками И сохранениями в гардероб
    conversion_query = (
        select(
            Product.id,
            Product.name,
            func.count(func.distinct(Generation.id)).label("try_ons"),
            func.count(func.distinct(UserWardrobeItem.id)).label("saves")
        )
        .outerjoin(Generation, and_(
            Generation.product_id == Product.id,
            Generation.type == GenerationType.TRY_ON,
            Generation.created_at >= since
        ))
        .outerjoin(UserWardrobeItem, and_(
            UserWardrobeItem.original_product_id == Product.id,
            UserWardrobeItem.created_at >= since
        ))
        .group_by(Product.id, Product.name)
        .having(func.count(func.distinct(Generation.id)) > 0)
        .order_by(desc("try_ons"))
        .limit(limit)
    )
    
    conversion_result = await db.execute(conversion_query)
    conversions = conversion_result.all()
    
    return {
        "period_days": days,
        "top_tried_products": [
            {
                "product_id": p.id,
                "name": p.name,
                "try_on_count": p.try_on_count,
                "characteristics": p.characteristics
            }
            for p in top_tried
        ],
        "conversion_rate": [
            {
                "product_id": c.id,
                "name": c.name,
                "try_ons": c.try_ons,
                "saves": c.saves,
                "conversion_rate": round((c.saves / c.try_ons * 100) if c.try_ons > 0 else 0, 2)
            }
            for c in conversions
        ]
    }


@router.get("/users/engagement")
async def get_user_engagement(
    days: int = Query(default=30, ge=1, le=365),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    🔥 АНАЛИТИКА: Активность пользователей
    
    Показывает:
    - Сколько пользователей используют примерку
    - Сколько сохраняют в гардероб
    - Средний размер гардероба
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Пользователи с примерками
    users_with_tryons = (
        select(func.count(func.distinct(Generation.user_id)))
        .where(
            and_(
                Generation.type == GenerationType.TRY_ON,
                Generation.created_at >= since
            )
        )
    )
    
    # Пользователи с гардеробом
    users_with_wardrobe = (
        select(func.count(func.distinct(UserWardrobeItem.user_id)))
        .where(UserWardrobeItem.created_at >= since)
    )
    
    # Средний размер гардероба
    avg_wardrobe_size = (
        select(func.avg(func.count(UserWardrobeItem.id)))
        .group_by(UserWardrobeItem.user_id)
    )
    
    # Всего пользователей
    total_users = select(func.count(User.id))
    
    result_tryons = await db.execute(users_with_tryons)
    result_wardrobe = await db.execute(users_with_wardrobe)
    result_avg = await db.execute(avg_wardrobe_size)
    result_total = await db.execute(total_users)
    
    tryons_count = result_tryons.scalar() or 0
    wardrobe_count = result_wardrobe.scalar() or 0
    avg_size = result_avg.scalar() or 0
    total = result_total.scalar() or 0
    
    return {
        "period_days": days,
        "total_users": total,
        "users_with_try_ons": tryons_count,
        "users_with_wardrobe": wardrobe_count,
        "try_on_adoption_rate": round((tryons_count / total * 100) if total > 0 else 0, 2),
        "wardrobe_adoption_rate": round((wardrobe_count / total * 100) if total > 0 else 0, 2),
        "avg_wardrobe_size": round(avg_size, 1)
    }


@router.get("/characteristics/popular")
async def get_popular_characteristics(
    days: int = Query(default=30, ge=1, le=365),
    characteristic: str = Query(..., description="Characteristic key (e.g., 'color', 'size', 'style')"),
    limit: int = Query(default=10, ge=1, le=50),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    🔥 АНАЛИТИКА: Популярные характеристики
    
    Показывает какие цвета/размеры/стили популярны
    Анализирует как примерки так и сохранения в гардероб
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Из примерок
    tryons_query = (
        select(
            func.jsonb_extract_path_text(Product.characteristics, characteristic).label("value"),
            func.count(Generation.id).label("try_on_count")
        )
        .join(Generation, Generation.product_id == Product.id)
        .where(
            and_(
                Generation.type == GenerationType.TRY_ON,
                Generation.created_at >= since,
                func.jsonb_extract_path_text(Product.characteristics, characteristic).isnot(None)
            )
        )
        .group_by("value")
        .order_by(desc("try_on_count"))
        .limit(limit)
    )
    
    # Из гардероба
    wardrobe_query = (
        select(
            func.jsonb_extract_path_text(UserWardrobeItem.characteristics, characteristic).label("value"),
            func.count(UserWardrobeItem.id).label("save_count")
        )
        .where(
            and_(
                UserWardrobeItem.created_at >= since,
                func.jsonb_extract_path_text(UserWardrobeItem.characteristics, characteristic).isnot(None)
            )
        )
        .group_by("value")
        .order_by(desc("save_count"))
        .limit(limit)
    )
    
    tryons_result = await db.execute(tryons_query)
    wardrobe_result = await db.execute(wardrobe_query)
    
    tryons = tryons_result.all()
    wardrobe = wardrobe_result.all()
    
    return {
        "period_days": days,
        "characteristic": characteristic,
        "from_try_ons": [
            {"value": t.value, "count": t.try_on_count}
            for t in tryons
        ],
        "from_wardrobe": [
            {"value": w.value, "count": w.save_count}
            for w in wardrobe
        ]
    }


@router.get("/categories/trends")
async def get_category_trends(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    🔥 АНАЛИТИКА: Популярные категории
    
    Показывает какие категории одежды популярны:
    - По примеркам
    - По сохранениям в гардероб
    - По покупкам
    """
    from app.models.category import ProductCategory
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # По примеркам
    tryons_query = (
        select(
            ProductCategory.id,
            ProductCategory.name,
            func.count(Generation.id).label("try_on_count")
        )
        .join(Product, Product.category_id == ProductCategory.id)
        .join(Generation, Generation.product_id == Product.id)
        .where(
            and_(
                Generation.type == GenerationType.TRY_ON,
                Generation.created_at >= since
            )
        )
        .group_by(ProductCategory.id, ProductCategory.name)
        .order_by(desc("try_on_count"))
        .limit(limit)
    )
    
    # По сохранениям в гардероб
    saves_query = (
        select(
            ProductCategory.id,
            ProductCategory.name,
            func.count(UserWardrobeItem.id).label("save_count")
        )
        .join(Product, Product.category_id == ProductCategory.id)
        .join(UserWardrobeItem, UserWardrobeItem.original_product_id == Product.id)
        .where(
            and_(
                UserWardrobeItem.source == WardrobeItemSource.SHOP_PRODUCT,
                UserWardrobeItem.created_at >= since
            )
        )
        .group_by(ProductCategory.id, ProductCategory.name)
        .order_by(desc("save_count"))
        .limit(limit)
    )
    
    tryons_result = await db.execute(tryons_query)
    saves_result = await db.execute(saves_query)
    
    tryons = tryons_result.all()
    saves = saves_result.all()
    
    return {
        "period_days": days,
        "most_tried_categories": [
            {
                "category_id": t.id,
                "category_name": t.name,
                "try_on_count": t.try_on_count
            }
            for t in tryons
        ],
        "most_saved_categories": [
            {
                "category_id": s.id,
                "category_name": s.name,
                "save_count": s.save_count
            }
            for s in saves
        ]
    }
