"""
Categories API - Admin manages categories, shops and users can view
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from app.database import get_db
from app.api.deps import get_current_admin
from app.models.category import ProductCategory
from app.models.product import Product
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse
from typing import List

router = APIRouter()


@router.get("/", response_model=CategoryListResponse)
async def get_categories(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    parent_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories (public endpoint)
    Used by shops to select category for products
    Used by mobile for filtering
    """
    query = select(ProductCategory).order_by(ProductCategory.order, ProductCategory.name)
    
    if is_active is not None:
        query = query.where(ProductCategory.is_active == is_active)
    
    if parent_id is not None:
        query = query.where(ProductCategory.parent_id == parent_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get categories with pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    categories = result.scalars().all()
    
    # Add products count for each category
    categories_with_count = []
    for category in categories:
        count_query = select(func.count(Product.id)).where(Product.category_id == category.id)
        count_result = await db.execute(count_query)
        products_count = count_result.scalar() or 0
        
        category_dict = CategoryResponse.model_validate(category).model_dump()
        category_dict['products_count'] = products_count
        categories_with_count.append(CategoryResponse(**category_dict))
    
    return CategoryListResponse(categories=categories_with_count, total=total)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get single category"""
    query = select(ProductCategory).where(ProductCategory.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Add products count
    count_query = select(func.count(Product.id)).where(Product.category_id == category_id)
    count_result = await db.execute(count_query)
    products_count = count_result.scalar() or 0
    
    category_dict = CategoryResponse.model_validate(category).model_dump()
    category_dict['products_count'] = products_count
    
    return CategoryResponse(**category_dict)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new category (Admin only)
    """
    # Check if slug already exists
    existing = await db.execute(
        select(ProductCategory).where(ProductCategory.slug == category_data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category_data.slug}' already exists"
        )
    
    # Create category
    category = ProductCategory(**category_data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    category_dict = CategoryResponse.model_validate(category).model_dump()
    category_dict['products_count'] = 0
    
    return CategoryResponse(**category_dict)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update category (Admin only)
    """
    # Check category exists
    query = select(ProductCategory).where(ProductCategory.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    
    # Check slug uniqueness if updating
    if "slug" in update_data and update_data["slug"] != category.slug:
        existing = await db.execute(
            select(ProductCategory).where(ProductCategory.slug == update_data["slug"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{update_data['slug']}' already exists"
            )
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await db.commit()
    await db.refresh(category)
    
    # Add products count
    count_query = select(func.count(Product.id)).where(Product.category_id == category_id)
    count_result = await db.execute(count_query)
    products_count = count_result.scalar() or 0
    
    category_dict = CategoryResponse.model_validate(category).model_dump()
    category_dict['products_count'] = products_count
    
    return CategoryResponse(**category_dict)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete category (Admin only)
    
    NOTE: Products in this category will have category_id set to NULL
    """
    # Check category exists
    query = select(ProductCategory).where(ProductCategory.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Set category_id to NULL for all products in this category
    await db.execute(
        update(Product)
        .where(Product.category_id == category_id)
        .values(category_id=None)
    )
    
    # Delete category
    await db.delete(category)
    await db.commit()
    
    return None
