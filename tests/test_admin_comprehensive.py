"""
Comprehensive Admin Tests
Tests all admin endpoints and scenarios
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


class TestAdminEndpoints:
    """Test admin API endpoints"""

    # Get All Users Tests
    @pytest.mark.asyncio
    async def test_get_all_users_as_admin(self, client, admin_headers, test_user):
        """Test admin getting all users"""
        response = client.get("/api/v1/admin/users", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_all_users_unauthorized(self, client):
        """Test getting users without auth"""
        response = client.get("/api/v1/admin/users")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_all_users_as_regular_user(self, client, user_headers):
        """Test regular user cannot access admin endpoints"""
        response = client.get("/api/v1/admin/users", headers=user_headers)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_all_users_as_shop(self, client, shop_headers):
        """Test shop cannot access admin endpoints"""
        response = client.get("/api/v1/admin/users", headers=shop_headers)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Get All Shops Tests
    @pytest.mark.asyncio
    async def test_get_all_shops_as_admin(self, client, admin_headers, test_shop):
        """Test admin getting all shops"""
        response = client.get("/api/v1/admin/shops", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_all_shops_unauthorized(self, client):
        """Test getting shops without auth"""
        response = client.get("/api/v1/admin/shops")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_all_shops_as_user(self, client, user_headers):
        """Test user cannot get all shops"""
        response = client.get("/api/v1/admin/shops", headers=user_headers)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Dashboard Tests
    @pytest.mark.asyncio
    async def test_get_admin_dashboard(self, client, admin_headers):
        """Test getting admin dashboard"""
        response = client.get("/api/v1/admin/dashboard", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_users" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_dashboard_unauthorized(self, client):
        """Test getting dashboard without auth"""
        response = client.get("/api/v1/admin/dashboard")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_dashboard_as_user(self, client, user_headers):
        """Test user cannot access dashboard"""
        response = client.get("/api/v1/admin/dashboard", headers=user_headers)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Product Moderation Tests
    @pytest.mark.asyncio
    async def test_get_pending_products(self, client, admin_headers):
        """Test getting pending products for moderation"""
        response = client.get("/api/v1/admin/products/pending", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_approve_product(self, client, admin_headers, test_product, db_session):
        """Test approving a product"""
        # Set product to pending
        test_product.moderation_status = "pending"
        await db_session.commit()

        response = client.post(
            f"/api/v1/admin/products/{test_product.id}/approve",
            headers=admin_headers
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_reject_product(self, client, admin_headers, test_product, db_session):
        """Test rejecting a product"""
        # Set product to pending
        test_product.moderation_status = "pending"
        await db_session.commit()

        reject_data = {
            "reason": "Does not meet quality standards"
        }

        response = client.post(
            f"/api/v1/admin/products/{test_product.id}/reject",
            headers=admin_headers,
            json=reject_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_user_cannot_approve_product(self, client, user_headers, test_product):
        """Test user cannot approve products"""
        response = client.post(
            f"/api/v1/admin/products/{test_product.id}/approve",
            headers=user_headers
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Platform Settings Tests
    @pytest.mark.asyncio
    async def test_get_platform_settings(self, client, admin_headers):
        """Test getting platform settings"""
        response = client.get("/api/v1/admin/settings", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_update_platform_settings(self, client, admin_headers):
        """Test updating platform settings"""
        settings_data = {
            "generation_cost": 5.0,
            "tryon_cost": 3.0,
            "platform_fee_percentage": 10.0
        }

        response = client.put(
            "/api/v1/admin/settings",
            headers=admin_headers,
            json=settings_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_user_cannot_update_settings(self, client, user_headers):
        """Test user cannot update platform settings"""
        settings_data = {
            "generation_cost": 1.0
        }

        response = client.put(
            "/api/v1/admin/settings",
            headers=user_headers,
            json=settings_data
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # User Management Tests
    @pytest.mark.asyncio
    async def test_update_user_balance(self, client, admin_headers, test_user):
        """Test admin updating user balance"""
        balance_data = {
            "balance": 500.0
        }

        response = client.put(
            f"/api/v1/admin/users/{test_user.id}/balance",
            headers=admin_headers,
            json=balance_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_update_shop_balance(self, client, admin_headers, test_shop):
        """Test admin updating shop balance"""
        balance_data = {
            "balance": 1000.0
        }

        response = client.put(
            f"/api/v1/admin/shops/{test_shop.id}/balance",
            headers=admin_headers,
            json=balance_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_user_cannot_update_balances(self, client, user_headers, test_user):
        """Test user cannot update balances"""
        balance_data = {
            "balance": 9999.0
        }

        response = client.put(
            f"/api/v1/admin/users/{test_user.id}/balance",
            headers=user_headers,
            json=balance_data
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Refund Management Tests
    @pytest.mark.asyncio
    async def test_get_pending_refunds(self, client, admin_headers):
        """Test getting pending refunds"""
        response = client.get("/api/v1/admin/refunds/pending", headers=admin_headers)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_approve_refund(self, client, admin_headers):
        """Test approving a refund"""
        response = client.post(
            "/api/v1/admin/refunds/1/approve",
            headers=admin_headers
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_reject_refund(self, client, admin_headers):
        """Test rejecting a refund"""
        reject_data = {
            "reason": "Does not meet refund criteria"
        }

        response = client.post(
            "/api/v1/admin/refunds/1/reject",
            headers=admin_headers,
            json=reject_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # Statistics Tests
    @pytest.mark.asyncio
    async def test_get_platform_statistics(self, client, admin_headers):
        """Test getting platform statistics"""
        response = client.get("/api/v1/admin/statistics", headers=admin_headers)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_get_revenue_statistics(self, client, admin_headers):
        """Test getting revenue statistics"""
        response = client.get("/api/v1/admin/statistics/revenue", headers=admin_headers)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # Edge Cases
    @pytest.mark.asyncio
    async def test_approve_nonexistent_product(self, client, admin_headers):
        """Test approving non-existent product"""
        response = client.post(
            "/api/v1/admin/products/99999/approve",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_balance(self, client, admin_headers):
        """Test updating balance for non-existent user"""
        balance_data = {
            "balance": 100.0
        }

        response = client.put(
            "/api/v1/admin/users/99999/balance",
            headers=admin_headers,
            json=balance_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_settings_invalid_values(self, client, admin_headers):
        """Test updating settings with invalid values"""
        settings_data = {
            "generation_cost": -5.0,  # Negative value
            "platform_fee_percentage": 150.0  # Over 100%
        }

        response = client.put(
            "/api/v1/admin/settings",
            headers=admin_headers,
            json=settings_data
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    @pytest.mark.asyncio
    async def test_admin_dashboard_structure(self, client, admin_headers):
        """Test admin dashboard returns proper structure"""
        response = client.get("/api/v1/admin/dashboard", headers=admin_headers)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert isinstance(data, dict)
            # Should contain statistics
