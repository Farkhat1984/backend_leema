"""
Tests for payment endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.shop import Shop
from unittest.mock import AsyncMock, patch


@pytest.mark.payment
class TestPaymentEndpoints:
    """Test payment endpoints"""

    @pytest.mark.anyio
    async def test_create_top_up_payment(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test creating top-up payment"""
        with patch('app.services.payment_service.payment_service.create_top_up_payment') as mock_payment:
            mock_payment.return_value = {
                "order_id": "test_order_123",
                "approval_url": "https://paypal.com/approve",
                "amount": 50.0
            }

            payment_data = {
                "payment_type": "top_up",
                "amount": 50.0
            }
            response = await client.post(
                "/api/v1/payments/user/top-up",
                headers=auth_headers_user,
                json=payment_data
            )
            assert response.status_code == 200
            data = response.json()
            assert "order_id" in data
            assert "approval_url" in data
            assert data["amount"] == 50.0

    @pytest.mark.anyio
    async def test_create_top_up_payment_invalid_type(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test creating top-up with wrong payment type"""
        payment_data = {
            "payment_type": "product_rent",  # Wrong type
            "amount": 50.0
        }
        response = await client.post(
            "/api/v1/payments/user/top-up",
            headers=auth_headers_user,
            json=payment_data
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_create_top_up_payment_unauthorized(self, client: AsyncClient):
        """Test creating top-up without auth"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 50.0
        }
        response = await client.post(
            "/api/v1/payments/user/top-up",
            json=payment_data
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_create_rent_payment(
        self,
        client: AsyncClient,
        test_shop: Shop,
        test_product,
        auth_headers_shop: dict
    ):
        """Test creating product rent payment"""
        with patch('app.services.payment_service.payment_service.create_rent_payment') as mock_payment:
            mock_payment.return_value = {
                "order_id": "test_rent_order_123",
                "approval_url": "https://paypal.com/approve",
                "amount": 10.0
            }

            payment_data = {
                "payment_type": "product_rent",
                "amount": 10.0,
                "extra_data": {
                    "product_id": test_product.id,
                    "months": 1
                }
            }
            response = await client.post(
                "/api/v1/payments/shop/rent-product",
                headers=auth_headers_shop,
                json=payment_data
            )
            assert response.status_code == 200
            data = response.json()
            assert "order_id" in data
            assert "approval_url" in data

    @pytest.mark.anyio
    async def test_create_rent_payment_missing_product_id(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test creating rent payment without product_id"""
        payment_data = {
            "payment_type": "product_rent",
            "amount": 10.0,
            "extra_data": {
                "months": 1
            }
        }
        response = await client.post(
            "/api/v1/payments/shop/rent-product",
            headers=auth_headers_shop,
            json=payment_data
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_create_rent_payment_invalid_type(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test creating rent payment with wrong type"""
        payment_data = {
            "payment_type": "top_up",  # Wrong type
            "amount": 10.0,
            "extra_data": {
                "product_id": 1
            }
        }
        response = await client.post(
            "/api/v1/payments/shop/rent-product",
            headers=auth_headers_shop,
            json=payment_data
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_capture_payment(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict,
        db_session: AsyncSession
    ):
        """Test capturing payment"""
        with patch('app.services.payment_service.payment_service.capture_payment') as mock_capture:
            from app.models.transaction import Transaction, TransactionType, TransactionStatus

            # Create a transaction in the database for ownership verification
            from sqlalchemy import select
            transaction = Transaction(
                id=1,
                type=TransactionType.TOP_UP,
                amount=50.0,
                status=TransactionStatus.PENDING,
                user_id=test_user.id,
                paypal_order_id="test_order_123"
            )
            db_session.add(transaction)
            await db_session.commit()

            # Mock transaction
            mock_transaction = Transaction(
                id=1,
                type=TransactionType.TOP_UP,
                amount=50.0,
                status=TransactionStatus.COMPLETED,
                user_id=test_user.id
            )
            mock_capture.return_value = mock_transaction

            response = await client.post(
                "/api/v1/payments/capture/test_order_123",
                headers=auth_headers_user
            )
            assert response.status_code == 200
            data = response.json()
            assert "transaction_id" in data
            assert "status" in data

    @pytest.mark.anyio
    async def test_capture_payment_failed(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict,
        db_session: AsyncSession
    ):
        """Test capturing payment failure"""
        with patch('app.services.payment_service.payment_service.capture_payment') as mock_capture:
            # Create a transaction in the database for ownership verification
            from app.models.transaction import Transaction, TransactionType, TransactionStatus
            transaction = Transaction(
                id=1,
                type=TransactionType.TOP_UP,
                amount=50.0,
                status=TransactionStatus.PENDING,
                user_id=test_user.id,
                paypal_order_id="invalid_order"
            )
            db_session.add(transaction)
            await db_session.commit()
            
            mock_capture.return_value = None

            response = await client.post(
                "/api/v1/payments/capture/invalid_order",
                headers=auth_headers_user
            )
            assert response.status_code == 400

    @pytest.mark.anyio
    async def test_paypal_webhook(self, client: AsyncClient):
        """Test PayPal webhook handler"""
        webhook_data = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "supplementary_data": {
                    "related_ids": {
                        "order_id": "test_order_123"
                    }
                }
            }
        }
        response = await client.post(
            "/api/v1/payments/paypal/webhook",
            json=webhook_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    @pytest.mark.anyio
    async def test_user_cannot_access_shop_payment(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test that user cannot create shop payments"""
        payment_data = {
            "payment_type": "product_rent",
            "amount": 10.0,
            "extra_data": {"product_id": 1}
        }
        response = await client.post(
            "/api/v1/payments/shop/rent-product",
            headers=auth_headers_user,
            json=payment_data
        )
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_create_shop_top_up_payment(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test creating shop top-up payment"""
        with patch('app.services.payment_service.payment_service.create_shop_top_up_payment') as mock_payment:
            mock_payment.return_value = {
                "order_id": "test_shop_order_123",
                "approval_url": "https://paypal.com/approve",
                "amount": 100.0
            }

            payment_data = {
                "payment_type": "top_up",
                "amount": 100.0
            }
            response = await client.post(
                "/api/v1/payments/shop/top-up",
                headers=auth_headers_shop,
                json=payment_data
            )
            assert response.status_code == 200
            data = response.json()
            assert "order_id" in data
            assert "approval_url" in data
            assert data["amount"] == 100.0

    @pytest.mark.anyio
    async def test_create_shop_top_up_invalid_type(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test creating shop top-up with wrong payment type"""
        payment_data = {
            "payment_type": "product_rent",  # Wrong type
            "amount": 100.0
        }
        response = await client.post(
            "/api/v1/payments/shop/top-up",
            headers=auth_headers_shop,
            json=payment_data
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_create_shop_top_up_unauthorized(
        self,
        client: AsyncClient
    ):
        """Test creating shop top-up without auth"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 100.0
        }
        response = await client.post(
            "/api/v1/payments/shop/top-up",
            json=payment_data
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_shop_cannot_access_user_payment(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test that shop cannot create user payments"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 50.0
        }
        response = await client.post(
            "/api/v1/payments/user/top-up",
            headers=auth_headers_shop,
            json=payment_data
        )
        assert response.status_code == 401
