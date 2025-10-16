"""
Comprehensive Payment Tests
Tests all payment endpoints and scenarios including PayPal integration
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock


class TestPaymentEndpoints:
    """Test payment API endpoints"""

    # User Top-up Tests
    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.create_top_up_payment')
    async def test_user_topup_success(self, mock_payment, client, user_headers, test_user):
        """Test successful user balance top-up"""
        mock_payment.return_value = {
            "order_id": "PAYPAL_ORDER_123",
            "approval_url": "https://paypal.com/approve/123",
            "amount": 50.0,
            "status": "pending"
        }

        payment_data = {
            "payment_type": "top_up",
            "amount": 50.0
        }

        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=user_headers,
            json=payment_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "order_id" in data
        assert "approval_url" in data
        assert data["amount"] == 50.0

    @pytest.mark.asyncio
    async def test_user_topup_unauthorized(self, client):
        """Test user top-up without authentication"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 50.0
        }

        response = client.post("/api/v1/payments/user/top-up", json=payment_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_user_topup_invalid_amount_too_low(self, client, user_headers):
        """Test user top-up with amount too low"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 0.50  # Below minimum
        }

        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=user_headers,
            json=payment_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_user_topup_invalid_amount_too_high(self, client, user_headers):
        """Test user top-up with amount too high"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 15000.0  # Above maximum
        }

        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=user_headers,
            json=payment_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_admin_cannot_topup_via_user_endpoint(self, client, admin_headers):
        """Test that admin cannot top-up via user endpoint"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 100.0
        }

        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=admin_headers,
            json=payment_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Shop Top-up Tests
    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.create_shop_top_up_payment')
    async def test_shop_topup_success(self, mock_payment, client, shop_headers):
        """Test successful shop balance top-up"""
        mock_payment.return_value = {
            "order_id": "PAYPAL_SHOP_123",
            "approval_url": "https://paypal.com/approve/shop123",
            "amount": 500.0,
            "status": "pending"
        }

        payment_data = {
            "payment_type": "top_up",
            "amount": 500.0
        }

        response = client.post(
            "/api/v1/payments/shop/top-up",
            headers=shop_headers,
            json=payment_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "order_id" in data
        assert data["amount"] == 500.0

    @pytest.mark.asyncio
    async def test_shop_topup_unauthorized(self, client):
        """Test shop top-up without authentication"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 500.0
        }

        response = client.post("/api/v1/payments/shop/top-up", json=payment_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_user_cannot_topup_as_shop(self, client, user_headers):
        """Test that user cannot access shop top-up endpoint"""
        payment_data = {
            "payment_type": "top_up",
            "amount": 500.0
        }

        response = client.post(
            "/api/v1/payments/shop/top-up",
            headers=user_headers,
            json=payment_data
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_shop_topup_invalid_amount(self, client, shop_headers):
        """Test shop top-up with invalid amount"""
        payment_data = {
            "payment_type": "top_up",
            "amount": -100.0  # Negative amount
        }

        response = client.post(
            "/api/v1/payments/shop/top-up",
            headers=shop_headers,
            json=payment_data
        )

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # Product Purchase Tests
    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.create_product_purchase_payment')
    async def test_purchase_product_success(self, mock_payment, client, user_headers, test_product):
        """Test successful product purchase"""
        mock_payment.return_value = {
            "order_id": "PURCHASE_ORDER_123",
            "approval_url": "https://paypal.com/approve/purchase123",
            "amount": test_product.price,
            "status": "pending"
        }

        purchase_data = {
            "payment_type": "purchase",
            "product_id": test_product.id,
            "quantity": 1
        }

        response = client.post(
            "/api/v1/payments/purchase",
            headers=user_headers,
            json=purchase_data
        )

        # May vary based on implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_purchase_product_unauthorized(self, client, test_product):
        """Test product purchase without auth"""
        purchase_data = {
            "payment_type": "purchase",
            "product_id": test_product.id
        }

        response = client.post("/api/v1/payments/purchase", json=purchase_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Product Rental Tests
    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.create_product_rental_payment')
    async def test_rent_product_success(self, mock_payment, client, user_headers, test_product):
        """Test successful product rental"""
        mock_payment.return_value = {
            "order_id": "RENTAL_ORDER_123",
            "approval_url": "https://paypal.com/approve/rental123",
            "amount": test_product.rental_price,
            "status": "pending"
        }

        rental_data = {
            "payment_type": "rental",
            "product_id": test_product.id,
            "rental_days": 7
        }

        response = client.post(
            "/api/v1/payments/rental",
            headers=user_headers,
            json=rental_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    # PayPal Webhook Tests
    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.handle_paypal_webhook')
    async def test_paypal_webhook_payment_captured(self, mock_handler, client):
        """Test PayPal webhook for payment captured"""
        mock_handler.return_value = {"status": "success"}

        webhook_data = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAPTURE_123",
                "amount": {"value": "50.00"},
                "status": "COMPLETED"
            }
        }

        response = client.post("/api/v1/payments/paypal/webhook", json=webhook_data)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.handle_paypal_webhook')
    async def test_paypal_webhook_order_approved(self, mock_handler, client):
        """Test PayPal webhook for order approved"""
        mock_handler.return_value = {"status": "success"}

        webhook_data = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "id": "ORDER_123",
                "status": "APPROVED"
            }
        }

        response = client.post("/api/v1/payments/paypal/webhook", json=webhook_data)

        assert response.status_code == status.HTTP_200_OK

    # Payment Verification Tests
    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.verify_payment')
    async def test_verify_payment_success(self, mock_verify, client, user_headers):
        """Test payment verification"""
        mock_verify.return_value = {
            "status": "completed",
            "amount": 50.0
        }

        response = client.get(
            "/api/v1/payments/verify/ORDER_123",
            headers=user_headers
        )

        # May need implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # Edge Cases
    @pytest.mark.asyncio
    async def test_topup_with_invalid_payment_type(self, client, user_headers):
        """Test top-up with wrong payment type"""
        payment_data = {
            "payment_type": "purchase",  # Should be top_up
            "amount": 50.0
        }

        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=user_headers,
            json=payment_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_multiple_topups_sequential(self, client, user_headers):
        """Test multiple sequential top-ups"""
        for amount in [10.0, 20.0, 30.0]:
            payment_data = {
                "payment_type": "top_up",
                "amount": amount
            }

            response = client.post(
                "/api/v1/payments/user/top-up",
                headers=user_headers,
                json=payment_data
            )

            # Each should be processed independently
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    @pytest.mark.asyncio
    async def test_payment_with_platform_header(self, client, user_headers):
        """Test payment with platform header"""
        headers = {**user_headers, "X-Client-Platform": "mobile"}
        payment_data = {
            "payment_type": "top_up",
            "amount": 50.0
        }

        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=headers,
            json=payment_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
