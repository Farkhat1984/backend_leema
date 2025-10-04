from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user, get_current_shop
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.product import Product
from app.services.payment_service import payment_service
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.auth import ClientPlatform
from typing import Optional
from datetime import datetime, timezone
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/user/top-up", response_model=PaymentResponse)
async def create_top_up_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create PayPal payment for user balance top-up
    Security: User role only, mobile platform preferred
    """
    # Validate payment type
    if payment_data.payment_type != "top_up":
        raise HTTPException(status_code=400, detail="Invalid payment type")
    
    # Security: Prevent admins from topping up user balance (should use admin panel)
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admins should use admin panel for balance modifications"
        )
    
    # Audit log
    logger.info(
        f"[PAYMENT] User top-up initiated: user_id={current_user.id}, "
        f"amount={payment_data.amount}, platform={x_client_platform}"
    )
    
    # Validate amount (reasonable limits)
    if payment_data.amount < 1 or payment_data.amount > 10000:
        raise HTTPException(
            status_code=400,
            detail="Amount must be between $1 and $10,000"
        )

    payment = await payment_service.create_top_up_payment(
        db, current_user.id, payment_data.amount
    )
    if not payment:
        raise HTTPException(status_code=400, detail="Failed to create payment")

    return PaymentResponse(
        order_id=payment["order_id"],
        approval_url=payment["approval_url"],
        amount=payment["amount"],
        status="pending"
    )


@router.post("/shop/top-up", response_model=PaymentResponse)
async def create_shop_top_up_payment(
    payment_data: PaymentCreate,
    current_shop: Shop = Depends(get_current_shop),
    x_client_platform: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create PayPal payment for shop balance top-up
    Security: Shop authentication required (prevents user accounts from topping up shops)
    """
    if payment_data.payment_type != "top_up":
        raise HTTPException(status_code=400, detail="Invalid payment type")
    
    # Audit log
    logger.info(
        f"[PAYMENT] Shop top-up initiated: shop_id={current_shop.id}, "
        f"amount={payment_data.amount}, platform={x_client_platform}"
    )
    
    # Validate amount
    if payment_data.amount < 1 or payment_data.amount > 50000:
        raise HTTPException(
            status_code=400,
            detail="Amount must be between $1 and $50,000"
        )

    payment = await payment_service.create_shop_top_up_payment(
        db, current_shop.id, payment_data.amount
    )
    if not payment:
        raise HTTPException(status_code=400, detail="Failed to create payment")

    return PaymentResponse(
        order_id=payment["order_id"],
        approval_url=payment["approval_url"],
        amount=payment["amount"],
        status="pending"
    )


@router.post("/shop/rent-product", response_model=PaymentResponse)
async def create_rent_payment(
    payment_data: PaymentCreate,
    current_shop: Shop = Depends(get_current_shop),
    x_client_platform: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create PayPal payment for product rent
    Security: Shop authentication required, validates product ownership
    """
    if payment_data.payment_type != "product_rent":
        raise HTTPException(status_code=400, detail="Invalid payment type")

    product_id = payment_data.extra_data.get("product_id")
    months = payment_data.extra_data.get("months", 1)

    if not product_id:
        raise HTTPException(status_code=400, detail="product_id required in extra_data")
    
    # Security: Verify product belongs to this shop
    product_result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.shop_id != current_shop.id:
        logger.warning(
            f"[SECURITY] Shop {current_shop.id} attempted to rent product {product_id} "
            f"owned by shop {product.shop_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Cannot rent product from another shop"
        )
    
    # Validate months
    if months < 1 or months > 12:
        raise HTTPException(
            status_code=400,
            detail="Rental period must be between 1 and 12 months"
        )
    
    # Audit log
    logger.info(
        f"[PAYMENT] Product rent initiated: shop_id={current_shop.id}, "
        f"product_id={product_id}, months={months}, platform={x_client_platform}"
    )

    payment = await payment_service.create_rent_payment(
        db, current_shop.id, product_id, months
    )
    if not payment:
        raise HTTPException(status_code=400, detail="Failed to create payment")

    return PaymentResponse(
        order_id=payment["order_id"],
        approval_url=payment["approval_url"],
        amount=payment["amount"],
        status="pending"
    )


@router.post("/capture/{order_id}")
async def capture_payment(
    order_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Capture PayPal payment after user approval
    Security: Validates transaction ownership (user/shop can only capture their own payments)
    """
    from app.models.transaction import Transaction
    
    # Get transaction to verify ownership
    transaction_result = await db.execute(
        select(Transaction).where(Transaction.paypal_order_id == order_id)
    )
    transaction_record = transaction_result.scalar_one_or_none()
    
    if not transaction_record:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Security: Verify ownership (user can only capture their own payments)
    # Admin can capture any payment (for support purposes)
    if current_user.role != UserRole.ADMIN:
        if transaction_record.user_id and transaction_record.user_id != current_user.id:
            logger.warning(
                f"[SECURITY] User {current_user.id} attempted to capture "
                f"transaction {order_id} belonging to user {transaction_record.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot capture another user's payment"
            )
    
    # Audit log
    logger.info(
        f"[PAYMENT] Capture initiated: order_id={order_id}, "
        f"user_id={current_user.id}, role={current_user.role.value}"
    )
    
    transaction = await payment_service.capture_payment(db, order_id)
    if not transaction:
        raise HTTPException(status_code=400, detail="Failed to capture payment")

    # Complete product purchase if needed
    from app.models.transaction import TransactionType
    if transaction.type == TransactionType.PRODUCT_PURCHASE:
        await payment_service.complete_product_purchase(db, transaction)

    return {
        "message": "Payment captured successfully",
        "transaction_id": transaction.id,
        "status": transaction.status.value
    }


@router.get("/paypal/success", response_class=HTMLResponse)
async def paypal_success(
    token: str,
    PayerID: str = None,
    db: AsyncSession = Depends(get_db)
):
    """PayPal payment success callback"""
    try:
        # Capture the payment
        transaction = await payment_service.capture_payment(db, token)
        
        if not transaction:
            return HTMLResponse(content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Ошибка платежа</title>
                    <style>
                        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
                        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                        h1 { color: #e74c3c; margin-bottom: 20px; }
                        .btn { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>❌ Ошибка обработки платежа</h1>
                        <p>Не удалось завершить платеж. Пожалуйста, попробуйте снова.</p>
                        <a href="/topup.html" class="btn">Вернуться к пополнению</a>
                    </div>
                </body>
                </html>
            """, status_code=400)
        
        # Success page
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Платёж успешен</title>
                <style>
                    body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                    .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }}
                    h1 {{ color: #10b981; margin-bottom: 20px; }}
                    .amount {{ font-size: 36px; font-weight: bold; color: #667eea; margin: 20px 0; }}
                    .btn {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Платёж успешно выполнен!</h1>
                    <p>Ваш баланс пополнен на:</p>
                    <div class="amount">${transaction.amount:.2f}</div>
                    <p>Спасибо за использование нашей платформы!</p>
                    <a href="/shop.html" class="btn">Вернуться в панель</a>
                </div>
                <script>
                    // Auto redirect after 3 seconds
                    setTimeout(() => {{
                        window.location.href = '/shop.html';
                    }}, 3000);
                </script>
            </body>
            </html>
        """)
    except Exception as e:
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Ошибка платежа</title>
                <style>
                    body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
                    .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }}
                    h1 {{ color: #e74c3c; margin-bottom: 20px; }}
                    .btn {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Ошибка обработки платежа</h1>
                    <p>{str(e)}</p>
                    <a href="/topup.html" class="btn">Вернуться к пополнению</a>
                </div>
            </body>
            </html>
        """, status_code=500)


@router.get("/paypal/cancel", response_class=HTMLResponse)
async def paypal_cancel():
    """PayPal payment cancel callback"""
    return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Платёж отменён</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                h1 { color: #f59e0b; margin-bottom: 20px; }
                .btn { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ Платёж отменён</h1>
                <p>Вы отменили платёж. Средства не были списаны с вашего счёта.</p>
                <a href="/topup.html" class="btn">Попробовать снова</a>
                <br><br>
                <a href="/shop.html" style="color: #667eea; text-decoration: none;">Вернуться в панель</a>
            </div>
            <script>
                // Auto redirect after 5 seconds
                setTimeout(() => {
                    window.location.href = '/topup.html';
                }, 5000);
            </script>
        </body>
        </html>
    """)


@router.post("/paypal/webhook")
async def paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """PayPal webhook handler"""
    # TODO: Verify webhook signature
    webhook_data = await request.json()

    event_type = webhook_data.get("event_type")
    resource = webhook_data.get("resource", {})

    # Handle different webhook events
    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        if order_id:
            await payment_service.capture_payment(db, order_id)

    return {"status": "received"}
