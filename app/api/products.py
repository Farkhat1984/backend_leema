from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.api.deps import get_current_shop, get_current_user_optional, get_current_user
from app.models.shop import Shop
from app.models.review import Review
from app.models.user import User
from app.models.moderation import ModerationQueue
from app.services.product_service import product_service
from app.services.payment_service import payment_service
from app.core.websocket import connection_manager
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate, ProductList
from app.schemas.payment import PaymentResponse
from app.schemas.review import ReviewCreate, ReviewResponse
from app.schemas.webhook import (
    create_product_event,
    create_review_event,
    create_moderation_queue_event,
    WebhookEventType
)
from typing import List, Optional
from datetime import datetime, timezone
import os
import uuid
from pathlib import Path

router = APIRouter()


@router.get("/", response_model=ProductList)
async def get_products(
    skip: int = 0,
    limit: int = 50,
    search: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get active approved products"""
    products, total = await product_service.get_active_products(db, skip, limit, search)
    return ProductList(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/search", response_model=ProductList)
async def search_products(
    skip: int = 0,
    limit: int = 50,
    query: str = None,
    shop_id: int = None,
    min_price: float = None,
    max_price: float = None,
    is_active: bool = None,
    moderation_status: str = None,
    sort_by: str = "created_at",  # created_at, price, views_count, purchases_count
    sort_order: str = "desc",  # asc, desc
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced product search with filters
    - query: text search in name/description
    - shop_id: filter by shop
    - min_price, max_price: price range
    - is_active: only active products
    - moderation_status: pending, approved, rejected
    - sort_by: field to sort by
    - sort_order: asc or desc
    """
    from app.models.product import Product, ModerationStatus
    from sqlalchemy import or_, and_
    
    # Build query
    search_query = select(Product)
    
    # Text search
    if query:
        search_query = search_query.where(
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
        )
    
    # Shop filter
    if shop_id:
        search_query = search_query.where(Product.shop_id == shop_id)
    
    # Price range
    if min_price is not None:
        search_query = search_query.where(Product.price >= min_price)
    if max_price is not None:
        search_query = search_query.where(Product.price <= max_price)
    
    # Active filter
    if is_active is not None:
        search_query = search_query.where(Product.is_active == is_active)
    
    # Moderation status
    if moderation_status:
        try:
            status_enum = ModerationStatus(moderation_status)
            search_query = search_query.where(Product.moderation_status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid moderation_status. Must be one of: {[s.value for s in ModerationStatus]}"
            )
    
    # Sorting
    sort_field = getattr(Product, sort_by, Product.created_at)
    if sort_order == "asc":
        search_query = search_query.order_by(sort_field.asc())
    else:
        search_query = search_query.order_by(sort_field.desc())
    
    # Count total
    count_query = select(func.count()).select_from(search_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    search_query = search_query.offset(skip).limit(limit)
    
    # Execute
    result = await db.execute(search_query)
    products = result.scalars().all()
    
    return ProductList(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get product by ID"""
    product = await product_service.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Increment views
    await product_service.increment_views(db, product_id)

    return ProductResponse.model_validate(product)


@router.post("/upload-images")
async def upload_product_images(
    files: List[UploadFile] = File(...),
    current_shop: Shop = Depends(get_current_shop)
):
    """Upload product images (shop only)"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate file types
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: jpeg, jpg, png, webp"
            )

    # Save files
    upload_dir = Path("uploads/products")
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_urls = []
    for file in files:
        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = upload_dir / unique_filename

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Return full URL with API domain
        from app.config import settings
        # Use UPLOAD_URL_PREFIX if set (for CDN), otherwise use API domain
        base_url = settings.UPLOAD_URL_PREFIX if settings.UPLOAD_URL_PREFIX else "https://api.leema.kz"
        saved_urls.append(f"{base_url}/uploads/products/{unique_filename}")

    return {"urls": saved_urls}


@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    characteristics: Optional[str] = Form(None),
    image_urls: Optional[str] = Form(None),
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Create new product (shop only)"""
    import json

    # Validate inputs
    if not name or len(name.strip()) == 0:
        raise HTTPException(status_code=422, detail="Product name cannot be empty")
    if price <= 0:
        raise HTTPException(status_code=422, detail="Product price must be positive")

    # Parse characteristics if provided
    chars = None
    if characteristics:
        try:
            chars = json.loads(characteristics)
        except:
            pass

    # Parse image URLs if provided
    images = None
    if image_urls:
        try:
            # Try parsing as JSON array first
            images = json.loads(image_urls)
            if not isinstance(images, list):
                images = None
        except:
            # Fallback to comma-separated string
            images = [url.strip() for url in image_urls.split(',') if url.strip()]

    product_data = ProductCreate(
        name=name,
        description=description,
        price=price,
        characteristics=chars,
        images=images
    )

    product = await product_service.create(db, current_shop.id, product_data)

    # Send webhook to admins about new product in moderation queue
    pending_count_result = await db.execute(
        select(func.count(ModerationQueue.id)).where(ModerationQueue.reviewed_at.is_(None))
    )
    pending_count = pending_count_result.scalar() or 0

    queue_event = create_moderation_queue_event(
        pending_count=pending_count,
        action="added",
        product_id=product.id
    )
    
    # Log and send to admins
    import logging
    logger = logging.getLogger(__name__)
    queue_event_dict = queue_event.model_dump(mode='json')
    logger.info(f"🔔 Sending moderation queue event to admins: {queue_event_dict}")
    await connection_manager.broadcast_to_type(queue_event_dict, "admin")
    logger.info(f"✅ Moderation queue event sent to admins")

    # Prepare full product data for WebSocket event
    product_dict = ProductResponse.model_validate(product).model_dump(mode='json')
    
    # Send webhook to ALL shops (mobile apps need to see all products)
    product_event = create_product_event(
        event_type=WebhookEventType.PRODUCT_CREATED,
        product_id=product.id,
        product_name=product.name,
        shop_id=current_shop.id,
        action="created",
        moderation_status=product.moderation_status.value,
        is_active=product.is_active,
        product=product_dict
    )
    
    product_event_dict = product_event.model_dump(mode='json')
    logger.info(f"🔔 Broadcasting product.created event to ALL shops")
    await connection_manager.broadcast_to_type(product_event_dict, "shop")
    logger.info(f"✅ Product.created event broadcast to all shops")

    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Update product (shop only) - sends back to moderation"""
    product = await product_service.get_by_id(db, product_id)
    if not product or product.shop_id != current_shop.id:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update product and reset to pending moderation
    updated_product = await product_service.update(db, product_id, product_data)
    
    # Set back to pending moderation
    from app.models.product import ModerationStatus
    updated_product.moderation_status = ModerationStatus.PENDING
    updated_product.moderation_notes = None  # Clear previous notes
    
    # Add or update moderation queue
    moderation_result = await db.execute(
        select(ModerationQueue).where(ModerationQueue.product_id == product_id)
    )
    moderation_entry = moderation_result.scalar_one_or_none()
    
    if moderation_entry:
        # Update existing entry
        moderation_entry.submitted_at = datetime.now(timezone.utc)
        moderation_entry.reviewed_at = None
        moderation_entry.reviewed_by = None
        moderation_entry.notes = None
    else:
        # Create new entry
        moderation_entry = ModerationQueue(
            product_id=product_id,
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(moderation_entry)
    
    await db.commit()
    await db.refresh(updated_product)

    # Prepare full product data for WebSocket event
    product_dict = ProductResponse.model_validate(updated_product).model_dump(mode='json')
    
    # Send webhook to ALL shops (mobile apps need to see all products)
    product_event = create_product_event(
        event_type=WebhookEventType.PRODUCT_UPDATED,
        product_id=updated_product.id,
        product_name=updated_product.name,
        shop_id=current_shop.id,
        action="updated_pending_moderation",
        moderation_status=updated_product.moderation_status.value,
        is_active=updated_product.is_active,
        product=product_dict
    )
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔔 Broadcasting product.updated event to ALL shops")
    await connection_manager.broadcast_to_type(product_event.model_dump(mode='json'), "shop")
    
    # Notify admins about updated product in moderation queue
    pending_count_result = await db.execute(
        select(func.count(ModerationQueue.id)).where(ModerationQueue.reviewed_at.is_(None))
    )
    pending_count = pending_count_result.scalar() or 0
    
    queue_event = create_moderation_queue_event(
        pending_count=pending_count,
        action="updated",
        product_id=product_id
    )
    
    logger.info(f"🔔 Product {product_id} updated and sent back to moderation. Notifying admins.")
    await connection_manager.broadcast_to_type(queue_event.model_dump(mode='json'), "admin")

    return ProductResponse.model_validate(updated_product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Delete product (shop only) - synchronizes with admin panel"""
    product = await product_service.get_by_id(db, product_id)
    if not product or product.shop_id != current_shop.id:
        raise HTTPException(status_code=404, detail="Product not found")

    product_name = product.name
    was_pending = product.moderation_status.value == "pending"
    await product_service.delete(db, product_id)

    # Send webhook to ALL shops (mobile apps need to know about deletions)
    product_event = create_product_event(
        event_type=WebhookEventType.PRODUCT_DELETED,
        product_id=product_id,
        product_name=product_name,
        shop_id=current_shop.id,
        action="deleted"
    )
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔔 Broadcasting product.deleted event to ALL shops and admins")
    await connection_manager.broadcast_to_type(product_event.model_dump(mode='json'), "shop")
    await connection_manager.broadcast_to_type(product_event.model_dump(mode='json'), "admin")
    
    # If product was pending moderation, update queue count
    if was_pending:
        pending_count_result = await db.execute(
            select(func.count(ModerationQueue.id)).where(ModerationQueue.reviewed_at.is_(None))
        )
        pending_count = pending_count_result.scalar() or 0
        
        queue_event = create_moderation_queue_event(
            pending_count=pending_count,
            action="removed",
            product_id=product_id
        )
        await connection_manager.broadcast_to_type(queue_event.model_dump(mode='json'), "admin")


    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/purchase", response_model=PaymentResponse)
async def purchase_product(
    product_id: int,
    current_user = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Purchase product (user)"""
    from app.api.deps import get_current_user
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    payment = await payment_service.process_product_purchase(db, current_user.id, product_id)
    if not payment:
        raise HTTPException(status_code=400, detail="Failed to create payment")

    return PaymentResponse(
        order_id=payment["order_id"],
        approval_url=payment["approval_url"],
        amount=payment["amount"],
        status="pending"
    )


@router.post("/{product_id}/reviews", response_model=ReviewResponse)
async def create_review(
    product_id: int,
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create product review (user only)"""
    # Verify product exists
    product = await product_service.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if user already reviewed
    existing_review = await db.execute(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.product_id == product_id
        )
    )
    if existing_review.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    # Create review
    new_review = Review(
        user_id=current_user.id,
        product_id=product_id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    # Send webhook to shop about new review
    review_event = create_review_event(
        review_id=new_review.id,
        product_id=product_id,
        product_name=product.name,
        shop_id=product.shop_id,
        user_id=current_user.id,
        user_name=current_user.name,
        rating=review.rating,
        comment=review.comment
    )
    await connection_manager.send_to_client(review_event.model_dump(mode='json'), "shop", product.shop_id)

    # Return with user info
    response = ReviewResponse.model_validate(new_review)
    response.user_name = current_user.name
    response.user_avatar = current_user.avatar_url

    return response


@router.get("/{product_id}/reviews", response_model=List[ReviewResponse])
async def get_product_reviews(
    product_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get product reviews"""
    # Verify product exists
    product = await product_service.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get reviews with user info
    query = (
        select(Review, User.name, User.avatar_url)
        .join(User, Review.user_id == User.id)
        .where(Review.product_id == product_id)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    reviews = result.all()
    
    review_responses = []
    for review, user_name, user_avatar in reviews:
        response = ReviewResponse.model_validate(review)
        response.user_name = user_name
        response.user_avatar = user_avatar
        review_responses.append(response)
    
    return review_responses


@router.get("/{product_id}/reviews/stats")
async def get_product_review_stats(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get product review statistics"""
    # Verify product exists
    product = await product_service.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get stats
    from sqlalchemy import case
    stats_result = await db.execute(
        select(
            func.count(Review.id).label('total_reviews'),
            func.avg(Review.rating).label('average_rating'),
            func.sum(case((Review.rating == 5, 1), else_=0)).label('five_star'),
            func.sum(case((Review.rating == 4, 1), else_=0)).label('four_star'),
            func.sum(case((Review.rating == 3, 1), else_=0)).label('three_star'),
            func.sum(case((Review.rating == 2, 1), else_=0)).label('two_star'),
            func.sum(case((Review.rating == 1, 1), else_=0)).label('one_star'),
        ).where(Review.product_id == product_id)
    )
    stats = stats_result.one()
    
    return {
        "product_id": product_id,
        "total_reviews": stats.total_reviews,
        "average_rating": float(stats.average_rating) if stats.average_rating else 0.0,
        "rating_distribution": {
            "5": stats.five_star,
            "4": stats.four_star,
            "3": stats.three_star,
            "2": stats.two_star,
            "1": stats.one_star
        }
    }
