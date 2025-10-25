from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_shop, get_current_user
from app.models.shop import Shop
from app.models.user import User
from app.services.shop_service import shop_service
from app.schemas.shop import ShopResponse, ShopUpdate, ShopAnalytics, ShopList, ShopCreate
from app.schemas.product import ProductResponse
from app.schemas.transaction import TransactionResponse
from typing import List, Optional
import uuid
from pathlib import Path

router = APIRouter()


@router.get("/", response_model=ShopList)
async def get_shops(
    skip: int = 0,
    limit: int = 50,
    query: str = None,
    sort_by: str = "created_at",  # created_at, shop_name, products_count
    sort_order: str = "desc",  # asc, desc
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of approved shops with active products
    - query: search by shop name or description
    - sort_by: created_at, shop_name, products_count
    - sort_order: asc or desc
    - is_active: filter by active status
    """
    shops, total = await shop_service.get_shops_list(
        db, skip, limit, query, sort_by, sort_order, is_active
    )
    return ShopList(
        shops=shops,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.post("/", response_model=ShopResponse)
async def create_shop(
    google_id: str = Form(...),
    email: str = Form(...),
    shop_name: str = Form(...),
    owner_name: str = Form(...),
    description: Optional[str] = Form(None),
    avatar_url: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """Create new shop (admin or public registration)"""
    # Check if shop with this google_id or email already exists
    existing_shop = await shop_service.get_by_google_id(db, google_id)
    if existing_shop:
        raise HTTPException(status_code=400, detail="Shop with this Google ID already exists")
    
    existing_shop = await shop_service.get_by_email(db, email)
    if existing_shop:
        raise HTTPException(status_code=400, detail="Shop with this email already exists")
    
    # Create shop
    shop_data = ShopCreate(
        google_id=google_id,
        email=email,
        shop_name=shop_name,
        owner_name=owner_name,
        description=description,
        avatar_url=avatar_url,
        phone=phone,
        whatsapp_number=whatsapp_number,
        is_active=is_active
    )
    shop = await shop_service.create(db, shop_data)
    
    # Send WebSocket event for new shop
    from app.core.websocket import connection_manager
    from app.schemas.webhook import create_shop_event, WebhookEventType
    from app.schemas.shop import ShopListItem
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Prepare shop data for event
    shop_dict = ShopListItem(
        id=shop.id,
        shop_name=shop.shop_name,
        description=shop.description,
        avatar_url=shop.avatar_url,
        logo_url=shop.avatar_url,
        products_count=0,
        is_approved=shop.is_approved,
        is_active=shop.is_active,
        created_at=shop.created_at
    ).model_dump(mode='json')
    
    shop_event = create_shop_event(
        event_type=WebhookEventType.SHOP_CREATED,
        shop_id=shop.id,
        shop_name=shop.shop_name,
        owner_name=shop.owner_name,
        action="created",
        is_approved=shop.is_approved,
        is_active=shop.is_active,
        shop=shop_dict
    )
    
    # Broadcast to all users (mobile apps)
    await connection_manager.broadcast_to_type(shop_event.model_dump(mode='json'), "user")
    logger.info(f"✅ Shop created event sent: {shop.shop_name}")
    
    return ShopResponse.model_validate(shop)


@router.post("/upload-avatar")
async def upload_shop_avatar(
    file: UploadFile = File(...),
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Upload shop avatar/logo image"""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file type
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: jpeg, jpg, png, webp"
        )

    # Save file
    upload_dir = Path("uploads/shop_images")
    upload_dir.mkdir(parents=True, exist_ok=True)

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
    avatar_url = f"{base_url}/uploads/shop_images/{unique_filename}"

    # Update shop avatar_url
    shop_data = ShopUpdate(avatar_url=avatar_url)
    updated_shop = await shop_service.update(db, current_shop.id, shop_data)
    
    # Send WebSocket event for shop update
    from app.core.websocket import connection_manager
    from app.schemas.webhook import create_shop_event, WebhookEventType
    from app.schemas.shop import ShopListItem
    from sqlalchemy import select, func
    from app.models.product import Product
    
    # Get products count
    products_count_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.shop_id == updated_shop.id,
            Product.is_active == True
        )
    )
    products_count = products_count_result.scalar() or 0
    
    # Prepare shop data for event
    shop_dict = ShopListItem(
        id=updated_shop.id,
        shop_name=updated_shop.shop_name,
        description=updated_shop.description,
        avatar_url=updated_shop.avatar_url,
        logo_url=updated_shop.avatar_url,
        products_count=products_count,
        is_approved=updated_shop.is_approved,
        is_active=updated_shop.is_active,
        created_at=updated_shop.created_at
    ).model_dump(mode='json')
    
    shop_event = create_shop_event(
        event_type=WebhookEventType.SHOP_UPDATED,
        shop_id=updated_shop.id,
        shop_name=updated_shop.shop_name,
        owner_name=updated_shop.owner_name,
        action="updated",
        is_approved=updated_shop.is_approved,
        is_active=updated_shop.is_active,
        shop=shop_dict
    )
    
    # Broadcast to all users (mobile apps)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔔 Sending shop avatar updated event: {updated_shop.shop_name}")
    await connection_manager.broadcast_to_type(shop_event.model_dump(mode='json'), "user")
    logger.info(f"✅ Shop avatar updated event sent")
    
    return {
        "url": avatar_url,
        "message": "Avatar uploaded successfully"
    }


@router.get("/me", response_model=ShopResponse)
async def get_current_shop_info(
    current_shop: Shop = Depends(get_current_shop)
):
    """Get current shop information"""
    return ShopResponse.model_validate(current_shop)


@router.post("/me/debug-update")
async def debug_update_shop(
    request: Request,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to see raw request data"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Get raw body
    body = await request.body()
    logger.info(f"🐛 [DEBUG] Raw request body: {body.decode('utf-8')}")
    
    # Parse JSON
    import json
    data = json.loads(body)
    logger.info(f"🐛 [DEBUG] Parsed JSON: {data}")
    logger.info(f"🐛 [DEBUG] whatsapp_number in data: {'whatsapp_number' in data}")
    logger.info(f"🐛 [DEBUG] avatar_url in data: {'avatar_url' in data}")
    
    if 'whatsapp_number' in data:
        logger.info(f"🐛 [DEBUG] whatsapp_number value: {data['whatsapp_number']}")
    if 'avatar_url' in data:
        logger.info(f"🐛 [DEBUG] avatar_url value: {data['avatar_url']}")
    
    # Try to parse with Pydantic
    from app.schemas.shop import ShopUpdate
    try:
        shop_data = ShopUpdate(**data)
        logger.info(f"🐛 [DEBUG] Pydantic parsed successfully")
        logger.info(f"🐛 [DEBUG] shop_data.whatsapp_number = {shop_data.whatsapp_number}")
        logger.info(f"🐛 [DEBUG] shop_data.avatar_url = {shop_data.avatar_url}")
        logger.info(f"🐛 [DEBUG] model_dump(): {shop_data.model_dump()}")
        logger.info(f"🐛 [DEBUG] model_dump(exclude_unset=True): {shop_data.model_dump(exclude_unset=True)}")
        
        return {
            "status": "success",
            "raw_data": data,
            "pydantic_parsed": shop_data.model_dump(),
            "exclude_unset": shop_data.model_dump(exclude_unset=True)
        }
    except Exception as e:
        logger.error(f"🐛 [DEBUG] Pydantic validation error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "raw_data": data
        }


@router.put("/me", response_model=ShopResponse)
async def update_current_shop(
    shop_data: ShopUpdate,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Update current shop"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 [API] Updating shop {current_shop.id} ({current_shop.shop_name})")
    logger.info(f"📦 [API] Request data: {shop_data.model_dump()}")
    logger.info(f"📦 [API] Exclude unset: {shop_data.model_dump(exclude_unset=True)}")
    
    # ОТЛАДКА: Проверяем каждое поле отдельно
    logger.info(f"🔍 [API DEBUG] shop_data.phone = {shop_data.phone}")
    logger.info(f"🔍 [API DEBUG] shop_data.whatsapp_number = {shop_data.whatsapp_number}")
    logger.info(f"🔍 [API DEBUG] shop_data.avatar_url = {shop_data.avatar_url}")
    
    updated_shop = await shop_service.update(db, current_shop.id, shop_data)
    if not updated_shop:
        logger.error(f"❌ [API] Shop not found during update")
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Send WebSocket event for shop update
    from app.core.websocket import connection_manager
    from app.schemas.webhook import create_shop_event, WebhookEventType
    from app.schemas.shop import ShopListItem
    from sqlalchemy import select, func
    from app.models.product import Product
    
    # Get products count
    products_count_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.shop_id == updated_shop.id,
            Product.is_active == True
        )
    )
    products_count = products_count_result.scalar() or 0
    
    # Prepare shop data for event
    shop_dict = ShopListItem(
        id=updated_shop.id,
        shop_name=updated_shop.shop_name,
        description=updated_shop.description,
        avatar_url=updated_shop.avatar_url,
        logo_url=updated_shop.avatar_url,
        products_count=products_count,
        is_approved=updated_shop.is_approved,
        is_active=updated_shop.is_active,
        created_at=updated_shop.created_at
    ).model_dump(mode='json')
    
    shop_event = create_shop_event(
        event_type=WebhookEventType.SHOP_UPDATED,
        shop_id=updated_shop.id,
        shop_name=updated_shop.shop_name,
        owner_name=updated_shop.owner_name,
        action="updated",
        is_approved=updated_shop.is_approved,
        is_active=updated_shop.is_active,
        shop=shop_dict
    )
    
    # Broadcast to all users (mobile apps)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔔 Sending shop updated event: {updated_shop.shop_name}")
    await connection_manager.broadcast_to_type(shop_event.model_dump(mode='json'), "user")
    logger.info(f"✅ Shop updated event sent")
    
    return ShopResponse.model_validate(updated_shop)


@router.delete("/me")
async def delete_current_shop(
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    """Delete current shop and all associated data"""
    from app.core.websocket import connection_manager
    from app.schemas.webhook import create_shop_event, WebhookEventType
    
    shop_id = current_shop.id
    shop_name = current_shop.shop_name
    
    # Delete shop
    success = await shop_service.delete_shop(db, shop_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Send WebSocket event
    shop_event = create_shop_event(
        event_type=WebhookEventType.SHOP_DELETED,
        shop_id=shop_id,
        shop_name=shop_name,
        owner_name=current_shop.owner_name,
        action="deleted",
        is_approved=False,
        is_active=False,
        shop=None
    )
    
    # Broadcast to all users
    await connection_manager.broadcast_to_type(shop_event.model_dump(mode='json'), "user")
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Shop deleted event sent: {shop_name}")
    
    return {"message": "Shop deleted successfully"}


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


@router.get("/{shop_id}", response_model=ShopResponse)
async def get_shop_by_id(
    shop_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get shop details by ID (public)"""
    from app.services.shop_service import shop_service
    
    shop = await shop_service.get_by_id(db, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    return ShopResponse.model_validate(shop)


@router.post("/{shop_id}/products/{product_id}/whatsapp-inquiry")
async def create_whatsapp_inquiry(
    shop_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate WhatsApp link for product inquiry
    Returns a WhatsApp deep link that opens chat with the shop
    """
    from app.services.shop_service import shop_service
    from app.services.product_service import product_service
    from urllib.parse import quote
    
    # Get shop
    shop = await shop_service.get_by_id(db, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    if not shop.whatsapp_number:
        raise HTTPException(
            status_code=400, 
            detail="This shop does not have WhatsApp configured"
        )
    
    # Get product
    product = await product_service.get_by_id(db, product_id)
    if not product or product.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Increment product views/interactions (optional analytics)
    await product_service.increment_views(db, product_id)
    
    # Clean phone number (remove spaces, dashes, etc)
    phone = shop.whatsapp_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Ensure phone has country code
    if not phone.startswith("+"):
        # Assume Kazakhstan if no code (you can adjust this)
        if phone.startswith("7") or phone.startswith("8"):
            phone = f"+7{phone[1:]}"
        else:
            phone = f"+{phone}"
    
    # Create message with product details
    message = f"Здравствуйте! Интересует товар: {product.name}\n"
    if product.price:
        message += f"Цена: {product.price} ₸\n"
    message += f"\nID товара: {product.id}"
    
    # URL encode the message
    encoded_message = quote(message)
    
    # Generate WhatsApp link (universal format)
    whatsapp_url = f"https://wa.me/{phone}?text={encoded_message}"
    
    return {
        "whatsapp_url": whatsapp_url,
        "shop_name": shop.shop_name,
        "product_name": product.name,
        "product_price": float(product.price),
        "message": "WhatsApp link generated successfully"
    }
