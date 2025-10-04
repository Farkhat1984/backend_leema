from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
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
from app.schemas.admin import (
    AdminSettings,
    AdminDashboard,
    ModerationAction,
    RefundAction,
    RefundResponse
)
from app.schemas.product import ProductResponse
from typing import List
from datetime import datetime, timezone

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
    await settings_service.set_setting(db, key, setting.value, setting.description)
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

        # Send email to shop
        from app.services.shop_service import shop_service
        shop = await shop_service.get_by_id(db, product.shop_id)
        if shop:
            await email_service.send_product_approved_notification(
                shop.email,
                shop.shop_name,
                product.name
            )

        return {"message": "Product approved successfully"}
    except ValueError as e:
        # Insufficient balance
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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

    product = await product_service.reject_product(db, product_id, admin.id, action.notes)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Send email to shop
    from app.services.shop_service import shop_service
    shop = await shop_service.get_by_id(db, product.shop_id)
    if shop:
        await email_service.send_product_rejected_notification(
            shop.email,
            shop.shop_name,
            product.name,
            action.notes
        )

    return {"message": "Product rejected successfully"}


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
        refund.processed_at = datetime.now(timezone.utc)

        # TODO: Process actual refund via PayPal
        # For MVP, just mark as completed
        refund.status = RefundStatus.COMPLETED

    elif action.action == "reject":
        refund.status = RefundStatus.REJECTED
        refund.admin_notes = action.admin_notes
        refund.processed_at = datetime.now(timezone.utc)

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
    user.updated_at = datetime.now(timezone.utc)
    
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
    approved = []
    failed = []
    
    for product_id in product_ids:
        try:
            product = await product_service.approve_product(db, product_id, admin.id, notes)
            if product:
                approved.append(product_id)
                
                # Send notification
                from app.services.shop_service import shop_service
                shop = await shop_service.get_by_id(db, product.shop_id)
                if shop:
                    await email_service.send_product_approved_notification(
                        shop.email,
                        shop.shop_name,
                        product.name
                    )
        except Exception as e:
            failed.append({"product_id": product_id, "error": str(e)})
    
    return {
        "message": f"Bulk approval completed: {len(approved)} succeeded, {len(failed)} failed",
        "approved": approved,
        "failed": failed
    }
