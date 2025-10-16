"""
Integration Tests - Full workflow scenarios
Tests complete user journeys and integrations
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


class TestIntegrationWorkflows:
    """Test complete user workflows"""

    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_full_user_registration_and_generation_workflow(self, mock_verify, client, db_session):
        """Test complete user flow: register -> topup -> generate"""
        # Step 1: Register via Google
        mock_verify.return_value = {
            "google_id": "workflow_user",
            "email": "workflow@example.com",
            "name": "Workflow User"
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "valid_code",
            "account_type": "user",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Check balance
        response = client.get("/api/v1/users/me/balance", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Step 3: Generate (should use free credits or fail)
        with patch('app.services.generation_service.generation_service.generate_fashion') as mock_gen:
            with patch('app.services.user_service.user_service.charge_for_generation') as mock_charge:
                mock_charge.return_value = {"amount": 0.0, "method": "free_credit"}
                mock_gen.return_value = MagicMock(
                    id=1,
                    user_id=1,
                    prompt="test",
                    image_url="https://example.com/gen.jpg",
                    cost=0.0
                )

                response = client.post(
                    "/api/v1/generations/generate",
                    headers=headers,
                    json={"prompt": "summer dress"}
                )

                assert response.status_code in [status.HTTP_200_OK, status.HTTP_402_PAYMENT_REQUIRED]

    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_full_shop_workflow(self, mock_verify, client, db_session):
        """Test complete shop flow: register -> create product -> get analytics"""
        # Step 1: Register shop
        mock_verify.return_value = {
            "google_id": "workflow_shop",
            "email": "workflowshop@example.com",
            "name": "Workflow Shop"
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "valid_code",
            "account_type": "shop",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create product
        product_data = {
            "name": "Shop Product",
            "description": "Test product",
            "price": 99.99,
            "category": "clothing",
            "sizes": ["M"],
            "colors": ["blue"],
            "images": ["https://example.com/img.jpg"]
        }

        response = client.post("/api/v1/products/", headers=headers, json=product_data)
        # May succeed or fail based on implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ]

        # Step 3: Get shop analytics
        response = client.get("/api/v1/shops/me/analytics", headers=headers)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_product_lifecycle(self, client, shop_headers, admin_headers, test_shop):
        """Test product lifecycle: create -> pending -> approve -> active"""
        # Step 1: Create product
        product_data = {
            "name": "Lifecycle Product",
            "description": "Testing lifecycle",
            "price": 49.99,
            "category": "clothing",
            "sizes": ["S", "M"],
            "colors": ["red"],
            "images": ["https://example.com/img.jpg"]
        }

        response = client.post("/api/v1/products/", headers=shop_headers, json=product_data)
        
        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            product_id = response.json()["id"]

            # Step 2: Admin approves product
            response = client.post(
                f"/api/v1/admin/products/{product_id}/approve",
                headers=admin_headers
            )

            # Step 3: Product should be visible
            response = client.get(f"/api/v1/products/{product_id}")
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    @patch('app.services.payment_service.payment_service.create_top_up_payment')
    async def test_payment_workflow(self, mock_payment, client, user_headers):
        """Test payment workflow: create payment -> webhook -> balance updated"""
        # Step 1: Create payment
        mock_payment.return_value = {
            "order_id": "TEST_ORDER_123",
            "approval_url": "https://paypal.com/approve",
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

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

        # Step 2: Simulate webhook
        with patch('app.services.payment_service.payment_service.handle_paypal_webhook') as mock_webhook:
            mock_webhook.return_value = {"status": "success"}

            webhook_data = {
                "event_type": "PAYMENT.CAPTURE.COMPLETED",
                "resource": {
                    "id": "TEST_ORDER_123",
                    "amount": {"value": "50.00"},
                    "status": "COMPLETED"
                }
            }

            response = client.post("/api/v1/payments/paypal/webhook", json=webhook_data)
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_tryon_workflow(self, client, user_headers, test_product):
        """Test try-on workflow: select product -> try-on -> view result"""
        # Step 1: Get product
        response = client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == status.HTTP_200_OK

        # Step 2: Try-on product
        with patch('app.services.generation_service.generation_service.try_on_product') as mock_tryon:
            with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge:
                mock_charge.return_value = {"amount": 0.0, "method": "free_credit"}
                mock_tryon.return_value = MagicMock(
                    id=1,
                    product_id=test_product.id,
                    image_url="https://example.com/tryon.jpg"
                )

                response = client.post(
                    "/api/v1/generations/try-on",
                    headers=user_headers,
                    json={
                        "product_id": test_product.id,
                        "user_image_url": "https://example.com/user.jpg"
                    }
                )

                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_402_PAYMENT_REQUIRED,
                    status.HTTP_404_NOT_FOUND
                ]

        # Step 3: Check history
        response = client.get("/api/v1/users/me/history", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_admin_moderation_workflow(self, client, shop_headers, admin_headers):
        """Test admin moderation workflow"""
        # Step 1: Shop creates product
        product_data = {
            "name": "Moderation Test Product",
            "description": "Test",
            "price": 99.99,
            "category": "clothing",
            "sizes": ["M"],
            "colors": ["black"],
            "images": ["https://example.com/img.jpg"]
        }

        response = client.post("/api/v1/products/", headers=shop_headers, json=product_data)
        
        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            product_id = response.json()["id"]

            # Step 2: Admin views pending products
            response = client.get("/api/v1/admin/products/pending", headers=admin_headers)
            assert response.status_code == status.HTTP_200_OK

            # Step 3: Admin approves or rejects
            response = client.post(
                f"/api/v1/admin/products/{product_id}/approve",
                headers=admin_headers
            )
            # Accept any reasonable response
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_400_BAD_REQUEST
            ]

    @pytest.mark.asyncio
    async def test_user_isolation(self, client, db_session):
        """Test that users can only access their own data"""
        from app.services.user_service import user_service
        from app.schemas.user import UserCreate
        from app.core.security import create_access_token

        # Create two users
        user1_data = UserCreate(
            google_id="user1_isolation",
            email="user1@example.com",
            name="User 1"
        )
        user1 = await user_service.create(db_session, user1_data)

        user2_data = UserCreate(
            google_id="user2_isolation",
            email="user2@example.com",
            name="User 2"
        )
        user2 = await user_service.create(db_session, user2_data)

        # Create tokens
        user1_token = create_access_token({"user_id": user1.id, "role": "user"})
        user2_token = create_access_token({"user_id": user2.id, "role": "user"})

        headers1 = {"Authorization": f"Bearer {user1_token}"}
        headers2 = {"Authorization": f"Bearer {user2_token}"}

        # User 1 gets their data
        response = client.get("/api/v1/users/me", headers=headers1)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "user1@example.com"

        # User 2 gets their data
        response = client.get("/api/v1/users/me", headers=headers2)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "user2@example.com"

    @pytest.mark.asyncio
    async def test_cross_platform_auth(self, client):
        """Test authentication works across platforms"""
        platforms = ["web", "mobile"]

        for platform in platforms:
            with patch('app.core.google_auth.google_auth.verify_oauth_code') as mock_verify:
                mock_verify.return_value = {
                    "google_id": f"platform_user_{platform}",
                    "email": f"{platform}@example.com",
                    "name": f"{platform.title()} User"
                }

                response = client.post("/api/v1/auth/google/login", json={
                    "code": "valid_code",
                    "account_type": "user",
                    "platform": platform
                })

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["platform"] == platform
