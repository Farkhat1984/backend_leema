from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
from app.database import get_db

logger = logging.getLogger(__name__)
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.shop import Shop
from app.models.product import Product, ModerationStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.generation import Generation
from app.models.moderation import ModerationQueue
from app.models.refund import Refund, RefundStatus
from app.models.settings import PlatformSettings
from app.services.product_service import product_service
from app.services.settings_service import settings_service
from app.core.email import email_service
from app.core.websocket import connection_manager
from app.schemas.admin import (
    AdminSettings,
    AdminDashboard,
    ModerationAction,
    RefundAction,
    RefundResponse,
    BulkProductAction,
    BulkShopAction
)
from app.schemas.product import ProductResponse
from app.schemas.webhook import (
    create_product_moderation_event,
    create_settings_update_event,
    create_moderation_queue_event,
    WebhookEventType
)
from typing import List
from app.core.datetime_utils import utc_now

router = APIRouter()


@router.get("/users")
async def get_all_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with balances"""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "balance": u.balance,
            "free_generations": u.free_generations_left,
            "free_try_ons": u.free_try_ons_left,
            "created_at": u.created_at
        }
        for u in users
    ]


@router.get("/shops")
async def get_all_shops(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all shops with balances"""
    result = await db.execute(
        select(Shop).order_by(Shop.created_at.desc())
    )
    shops = result.scalars().all()
    return [
        {
            "id": s.id,
            "shop_name": s.shop_name,
            "email": s.email,
            "balance": s.balance,
            "created_at": s.created_at
        }
        for s in shops
    ]


@router.get("/dashboard", response_model=AdminDashboard)
async def get_dashboard(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard statistics"""
    # Count users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0

    # Sum user balances
    user_balances_result = await db.execute(select(func.sum(User.balance)))
    total_user_balances = float(user_balances_result.scalar() or 0)

    # Count shops
    shops_result = await db.execute(select(func.count(Shop.id)))
    total_shops = shops_result.scalar() or 0

    # Sum shop balances
    shop_balances_result = await db.execute(select(func.sum(Shop.balance)))
    total_shop_balances = float(shop_balances_result.scalar() or 0)

    # Count products
    products_result = await db.execute(select(func.count(Product.id)))
    total_products = products_result.scalar() or 0

    active_products_result = await db.execute(
        select(func.count(Product.id)).where(Product.is_active == True)
    )
    active_products = active_products_result.scalar() or 0

    # Count generations
    generations_result = await db.execute(select(func.count(Generation.id)))
    total_generations = generations_result.scalar() or 0

    # Calculate revenue
    revenue_result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.status == TransactionStatus.COMPLETED
        )
    )
    total_revenue = float(revenue_result.scalar() or 0)

    # Pending moderation
    moderation_result = await db.execute(
        select(func.count(ModerationQueue.id)).where(
            ModerationQueue.reviewed_at.is_(None)
        )
    )
    pending_moderation = moderation_result.scalar() or 0

    # Pending refunds
    refunds_result = await db.execute(
        select(func.count(Refund.id)).where(
            Refund.status == RefundStatus.REQUESTED
        )
    )
    pending_refunds = refunds_result.scalar() or 0

    return AdminDashboard(
        total_users=total_users,
        total_shops=total_shops,
        total_products=total_products,
        active_products=active_products,
        total_generations=total_generations,
        total_revenue=total_revenue,
        pending_moderation=pending_moderation,
        pending_refunds=pending_refunds,
        total_user_balances=total_user_balances,
        total_shop_balances=total_shop_balances
    )


@router.get("/settings", response_model=List[AdminSettings])
async def get_settings(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all platform settings"""
    result = await db.execute(select(PlatformSettings))
    settings = result.scalars().all()
    return [AdminSettings.model_validate(s, from_attributes=True) for s in settings]


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    setting: AdminSettings,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update platform setting"""
    # Get old value - get_setting returns str, not object!
    old_value = await settings_service.get_setting(db, key)

    await settings_service.set_setting(db, key, setting.value, setting.description)

    # Send webhook to all clients
    try:
        event = create_settings_update_event(
            key=key,
            new_value=setting.value,
            updated_by=admin.id,
            old_value=old_value,
            description=setting.description
        )
        await connection_manager.broadcast_to_all(event.model_dump(mode="json"))
    except Exception as e:
        # Log error but don't fail the request
        logger.warning(f"Failed to broadcast settings update: {e}")

    return {"message": "Setting updated successfully"}


@router.get("/moderation/queue", response_model=List[ProductResponse])
async def get_moderation_queue(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get products pending moderation"""
    result = await db.execute(
        select(Product)
        .join(ModerationQueue)
        .where(
            Product.moderation_status == ModerationStatus.PENDING,
            ModerationQueue.reviewed_at.is_(None)
        )
        .order_by(ModerationQueue.submitted_at.asc())
    )
    products = result.scalars().all()
    return [ProductResponse.model_validate(p) for p in products]


@router.post("/moderation/{product_id}/approve")
async def approve_product(
    product_id: int,
    action: ModerationAction,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approve product - charges shop for approval"""
    try:
        product = await product_service.approve_product(db, product_id, admin.id, action.notes)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Get shop info
        from app.services.shop_service import shop_service
        from app.services.settings_service import settings_service
        shop = await shop_service.get_by_id(db, product.shop_id)
        approval_fee = await settings_service.get_setting_float(db, "shop_approval_fee", 5.0)

        # Send webhook to shop
        event = create_product_moderation_event(
            event_type=WebhookEventType.PRODUCT_APPROVED,
            product_id=product.id,
            product_name=product.name,
            shop_id=product.shop_id,
            moderation_status="approved",
            admin_id=admin.id,
            shop_name=shop.shop_name if shop else None,
            moderation_notes=action.notes,
            approval_fee=approval_fee
        )
        await connection_manager.send_to_client(event.model_dump(mode="json"), "shop", product.shop_id)

        # Broadcast to all users (mobile app users)
        await connection_manager.broadcast_to_type(event.model_dump(mode="json"), "user")

        # Update moderation queue for admins
        pending_count_result = await db.execute(
            select(func.count(ModerationQueue.id)).where(ModerationQueue.reviewed_at.is_(None))
        )
        pending_count = pending_count_result.scalar() or 0
        queue_event = create_moderation_queue_event(
            pending_count=pending_count,
            action="processed",
            product_id=product_id
        )
        await connection_manager.broadcast_to_type(queue_event.model_dump(mode="json"), "admin")

        # Send email to shop (non-critical, don't fail if email fails)
        try:
            if shop and shop.email:
                await email_service.send_product_approved_notification(
                    shop.email,
                    shop.shop_name,
                    product.name
                )
        except Exception as email_error:
            # Log email error but don't fail the approval
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send approval email for product {product_id}: {email_error}")

        return {"message": "Product approved successfully"}
    except ValueError as e:
        # Insufficient balance
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error approving product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error approving product: {str(e)}")


@router.post("/moderation/{product_id}/reject")
async def reject_product(
    product_id: int,
    action: ModerationAction,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reject product"""
    if not action.notes:
        raise HTTPException(status_code=400, detail="Notes required for rejection")

    try:
        product = await product_service.reject_product(db, product_id, admin.id, action.notes)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Get shop info
        from app.services.shop_service import shop_service
        shop = await shop_service.get_by_id(db, product.shop_id)

        # Send webhook to shop
        event = create_product_moderation_event(
            event_type=WebhookEventType.PRODUCT_REJECTED,
            product_id=product.id,
            product_name=product.name,
            shop_id=product.shop_id,
            moderation_status="rejected",
            admin_id=admin.id,
            shop_name=shop.shop_name if shop else None,
            moderation_notes=action.notes
        )
        await connection_manager.send_to_client(event.model_dump(mode="json"), "shop", product.shop_id)

        # Update moderation queue for admins
        pending_count_result = await db.execute(
            select(func.count(ModerationQueue.id)).where(ModerationQueue.reviewed_at.is_(None))
        )
        pending_count = pending_count_result.scalar() or 0
        queue_event = create_moderation_queue_event(
            pending_count=pending_count,
            action="processed",
            product_id=product_id
        )
        await connection_manager.broadcast_to_type(queue_event.model_dump(mode="json"), "admin")

        # Send email to shop (non-critical, don't fail if email fails)
        try:
            if shop and shop.email:
                await email_service.send_product_rejected_notification(
                    shop.email,
                    shop.shop_name,
                    product.name,
                    action.notes
                )
        except Exception as email_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send rejection email for product {product_id}: {email_error}")

        return {"message": "Product rejected successfully"}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error rejecting product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error rejecting product: {str(e)}")


@router.get("/refunds", response_model=List[RefundResponse])
async def get_refund_requests(
    status: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get refund requests"""
    query = select(Refund)
    if status:
        query = query.where(Refund.status == status)
    query = query.order_by(Refund.created_at.desc())

    result = await db.execute(query)
    refunds = result.scalars().all()
    return [RefundResponse.model_validate(r) for r in refunds]


@router.post("/refunds/{refund_id}/process")
async def process_refund(
    refund_id: int,
    action: RefundAction,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Process refund request"""
    result = await db.execute(select(Refund).where(Refund.id == refund_id))
    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")

    if action.action == "approve":
        refund.status = RefundStatus.APPROVED
        refund.admin_notes = action.admin_notes
        refund.processed_at = utc_now()

        # TODO: Process actual refund via PayPal
        # For MVP, just mark as completed
        refund.status = RefundStatus.COMPLETED

    elif action.action == "reject":
        refund.status = RefundStatus.REJECTED
        refund.admin_notes = action.admin_notes
        refund.processed_at = utc_now()

    await db.commit()
    return {"message": f"Refund {action.action}d successfully"}


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed user information (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user transactions
    transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(10)
    )
    transactions = transactions_result.scalars().all()
    
    # Get user generations
    generations_result = await db.execute(
        select(Generation)
        .where(Generation.user_id == user_id)
        .order_by(Generation.created_at.desc())
        .limit(10)
    )
    generations = generations_result.scalars().all()
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "balance": user.balance,
        "free_generations_left": user.free_generations_left,
        "free_try_ons_left": user.free_try_ons_left,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "recent_transactions": [
            {
                "id": t.id,
                "type": t.type.value,
                "amount": t.amount,
                "status": t.status.value,
                "created_at": t.created_at
            } for t in transactions
        ],
        "recent_generations": [
            {
                "id": g.id,
                "prompt": g.prompt,
                "status": g.status,
                "created_at": g.created_at
            } for g in generations
        ]
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete or ban user (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == User.UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    
    # Soft delete - could add is_active field later
    # For now, just delete
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    new_role: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Change user role (admin only) - for role management"""
    from app.models.user import UserRole
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    try:
        role_enum = UserRole(new_role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
        )
    
    old_role = user.role.value
    user.role = role_enum
    user.updated_at = utc_now()
    
    await db.commit()
    
    return {
        "message": f"User role changed from {old_role} to {new_role}",
        "user_id": user_id,
        "old_role": old_role,
        "new_role": new_role
    }


@router.get("/transactions")
async def get_all_transactions(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all transactions across platform (admin only)"""
    query = select(Transaction).order_by(Transaction.created_at.desc())
    
    if status:
        try:
            status_enum = TransactionStatus(status)
            query = query.where(Transaction.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in TransactionStatus]}"
            )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    # Calculate totals
    totals_result = await db.execute(
        select(
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount')
        ).where(Transaction.status == TransactionStatus.COMPLETED)
    )
    totals = totals_result.one()
    
    return {
        "transactions": [
            {
                "id": t.id,
                "type": t.type.value,
                "amount": t.amount,
                "status": t.status.value,
                "user_id": t.user_id,
                "shop_id": t.shop_id,
                "description": t.description,
                "created_at": t.created_at
            } for t in transactions
        ],
        "total_count": totals.count,
        "total_amount": float(totals.total_amount or 0),
        "skip": skip,
        "limit": limit
    }


@router.post("/products/bulk-approve")
async def bulk_approve_products(
    product_ids: List[int],
    notes: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Bulk approve multiple products (admin only)"""
    from app.services.shop_service import shop_service
    approval_fee = await settings_service.get_setting_float(db, "shop_approval_fee", 5.0)
    
    approved = []
    failed = []
    
    for product_id in product_ids:
        try:
            product = await product_service.approve_product(db, product_id, admin.id, notes)
            if product:
                approved.append(product_id)
                
                # Get shop info
                shop = await shop_service.get_by_id(db, product.shop_id)
                
                # Send WebSocket notification to shop
                event = create_product_moderation_event(
                    event_type=WebhookEventType.PRODUCT_APPROVED,
                    product_id=product.id,
                    product_name=product.name,
                    shop_id=product.shop_id,
                    moderation_status="approved",
                    admin_id=admin.id,
                    shop_name=shop.shop_name if shop else None,
                    moderation_notes=notes,
                    approval_fee=approval_fee
                )
                await connection_manager.send_to_client(event.model_dump(mode="json"), "shop", product.shop_id)
                
                # Broadcast to all users (mobile app users)
                await connection_manager.broadcast_to_type(event.model_dump(mode="json"), "user")
                
                # Send email notification
                if shop:
                    try:
                        await email_service.send_product_approved_notification(
                            shop.email,
                            shop.shop_name,
                            product.name
                        )
                    except Exception as email_error:
                        logger.warning(f"Failed to send approval email for product {product_id}: {email_error}")
        except Exception as e:
            failed.append({"product_id": product_id, "error": str(e)})
    
    # Update moderation queue for admins
    pending_count_result = await db.execute(
        select(func.count(ModerationQueue.id)).where(ModerationQueue.reviewed_at.is_(None))
    )
    pending_count = pending_count_result.scalar() or 0
    queue_event = create_moderation_queue_event(
        pending_count=pending_count,
        action="processed",
        product_id=None  # Bulk action
    )
    await connection_manager.broadcast_to_type(queue_event.model_dump(mode="json"), "admin")
    
    return {
        "message": f"Bulk approval completed: {len(approved)} succeeded, {len(failed)} failed",
        "approved": approved,
        "failed": failed
    }


# === EXTENDED MANAGEMENT ENDPOINTS ===

@router.get("/products/all")
async def get_all_products_admin(
    status: str = None,  # pending, approved, rejected, all
    is_active: bool = None,
    shop_id: int = None,
    min_price: float = None,
    max_price: float = None,
    sort_by: str = "created_at",  # created_at, updated_at, price, name, views_count, try_ons_count, purchases_count
    sort_order: str = "desc",  # asc, desc
    page: int = 1,
    per_page: int = 50,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all products with advanced filtering and sorting"""
    
    # Build query
    query = select(Product)
    
    # Apply filters
    filters = []
    
    if status and status != "all":
        if status in ["pending", "approved", "rejected"]:
            filters.append(Product.moderation_status == ModerationStatus(status))
    
    if is_active is not None:
        filters.append(Product.is_active == is_active)
    
    if shop_id:
        filters.append(Product.shop_id == shop_id)
    
    if min_price is not None:
        filters.append(Product.price >= min_price)
    
    if max_price is not None:
        filters.append(Product.price <= max_price)
    
    if filters:
        query = query.where(*filters)
    
    # Count total
    count_query = select(func.count()).select_from(Product)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = Product.created_at  # default
    if sort_by == "updated_at":
        sort_column = Product.updated_at
    elif sort_by == "price":
        sort_column = Product.price
    elif sort_by == "name":
        sort_column = Product.name
    elif sort_by == "views_count":
        sort_column = Product.views_count
    elif sort_by == "try_ons_count":
        sort_column = Product.try_ons_count
    elif sort_by == "purchases_count":
        sort_column = Product.purchases_count
    
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Get shop info for each product
    product_list = []
    for product in products:
        shop_result = await db.execute(select(Shop).where(Shop.id == product.shop_id))
        shop = shop_result.scalar_one_or_none()
        
        product_dict = {
            "id": product.id,
            "shop_id": product.shop_id,
            "shop_name": shop.shop_name if shop else "Unknown",
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "images": product.images or [],
            "is_active": product.is_active,
            "moderation_status": product.moderation_status.value,
            "moderation_notes": product.moderation_notes,
            "views_count": product.views_count,
            "try_ons_count": product.try_ons_count,
            "purchases_count": product.purchases_count,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
            "rent_expires_at": product.rent_expires_at.isoformat() if product.rent_expires_at else None
        }
        product_list.append(product_dict)
    
    return {
        "products": product_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/shops/all")
async def get_all_shops_admin(
    is_approved: bool = None,
    min_balance: float = None,
    max_balance: float = None,
    sort_by: str = "created_at",  # created_at, shop_name, balance
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 50,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all shops with advanced filtering and sorting"""
    
    # Build query
    query = select(Shop)
    
    # Apply filters
    filters = []
    
    if is_approved is not None:
        filters.append(Shop.is_approved == is_approved)
    
    if min_balance is not None:
        filters.append(Shop.balance >= min_balance)
    
    if max_balance is not None:
        filters.append(Shop.balance <= max_balance)
    
    if filters:
        query = query.where(*filters)
    
    # Count total
    count_query = select(func.count()).select_from(Shop)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = Shop.created_at
    if sort_by == "shop_name":
        sort_column = Shop.shop_name
    elif sort_by == "balance":
        sort_column = Shop.balance
    
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    shops = result.scalars().all()
    
    # Get product counts for each shop
    shop_list = []
    for shop in shops:
        # Count products
        total_products_result = await db.execute(
            select(func.count()).select_from(Product).where(Product.shop_id == shop.id)
        )
        total_products = total_products_result.scalar()
        
        active_products_result = await db.execute(
            select(func.count()).select_from(Product).where(
                Product.shop_id == shop.id,
                Product.is_active == True
            )
        )
        active_products = active_products_result.scalar()
        
        pending_products_result = await db.execute(
            select(func.count()).select_from(Product).where(
                Product.shop_id == shop.id,
                Product.moderation_status == ModerationStatus.PENDING
            )
        )
        pending_products = pending_products_result.scalar()
        
        shop_dict = {
            "id": shop.id,
            "shop_name": shop.shop_name,
            "owner_name": shop.owner_name,
            "email": shop.email,
            "description": shop.description,
            "avatar_url": shop.avatar_url,
            "balance": float(shop.balance),
            "is_approved": shop.is_approved,
            "total_products": total_products,
            "active_products": active_products,
            "pending_products": pending_products,
            "created_at": shop.created_at.isoformat(),
            "updated_at": shop.updated_at.isoformat()
        }
        shop_list.append(shop_dict)
    
    return {
        "shops": shop_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/users/all")
async def get_all_users_admin(
    role: str = None,  # user, admin
    min_balance: float = None,
    max_balance: float = None,
    sort_by: str = "created_at",  # created_at, name, balance
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 50,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with advanced filtering and sorting"""
    
    # Build query
    query = select(User)
    
    # Apply filters
    filters = []
    
    if role:
        filters.append(User.role == role)
    
    if min_balance is not None:
        filters.append(User.balance >= min_balance)
    
    if max_balance is not None:
        filters.append(User.balance <= max_balance)
    
    if filters:
        query = query.where(*filters)
    
    # Count total
    count_query = select(func.count()).select_from(User)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = User.created_at
    if sort_by == "name":
        sort_column = User.name
    elif sort_by == "balance":
        sort_column = User.balance
    
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get activity stats for each user
    user_list = []
    for user in users:
        # Count generations
        generations_result = await db.execute(
            select(func.count()).select_from(Generation).where(Generation.user_id == user.id)
        )
        total_generations = generations_result.scalar()
        
        user_dict = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "balance": float(user.balance),
            "free_generations_left": user.free_generations_left,
            "free_try_ons_left": user.free_try_ons_left,
            "role": user.role,
            "total_generations": total_generations,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat()
        }
        user_list.append(user_dict)
    
    return {
        "users": user_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.post("/products/bulk-action")
async def bulk_product_action(
    bulk_action: BulkProductAction,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk actions on products"""
    
    success = []
    failed = []
    
    for product_id in bulk_action.product_ids:
        try:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            
            if not product:
                failed.append({"product_id": product_id, "error": "Product not found"})
                continue
            
            if bulk_action.action == "approve":
                product.moderation_status = ModerationStatus.APPROVED
                product.is_active = True
                if bulk_action.notes:
                    product.moderation_notes = bulk_action.notes
                    
            elif bulk_action.action == "reject":
                product.moderation_status = ModerationStatus.REJECTED
                product.is_active = False
                if bulk_action.notes:
                    product.moderation_notes = bulk_action.notes
                    
            elif bulk_action.action == "delete":
                await db.delete(product)
                
            elif bulk_action.action == "activate":
                product.is_active = True
                
            elif bulk_action.action == "deactivate":
                product.is_active = False
            
            await db.commit()
            success.append(product_id)
            
        except Exception as e:
            failed.append({"product_id": product_id, "error": str(e)})
    
    return {
        "message": f"Bulk action completed: {len(success)} succeeded, {len(failed)} failed",
        "success": success,
        "failed": failed
    }


@router.post("/shops/bulk-action")
async def bulk_shop_action(
    bulk_action: BulkShopAction,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk actions on shops"""
    
    success = []
    failed = []
    
    for shop_id in bulk_action.shop_ids:
        try:
            result = await db.execute(select(Shop).where(Shop.id == shop_id))
            shop = result.scalar_one_or_none()
            
            if not shop:
                failed.append({"shop_id": shop_id, "error": "Shop not found"})
                continue
            
            if bulk_action.action == "approve":
                shop.is_approved = True
            elif bulk_action.action == "block":
                shop.is_approved = False
            
            await db.commit()
            success.append(shop_id)
            
        except Exception as e:
            failed.append({"shop_id": shop_id, "error": str(e)})
    
    return {
        "message": f"Bulk action completed: {len(success)} succeeded, {len(failed)} failed",
        "success": success,
        "failed": failed
    }


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a product"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.delete(product)
    await db.commit()
    
    return {"message": "Product deleted successfully"}
