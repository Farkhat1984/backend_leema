"""
Comprehensive User Tests
Tests all user endpoints and scenarios
"""
import pytest
from fastapi import status


class TestUserEndpoints:
    """Test user API endpoints"""

    # Get Current User Tests
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, user_headers, test_user):
        """Test getting current user info"""
        response = client.get("/api/v1/users/me", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert "balance" in data
        assert "free_generations_left" in data

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client):
        """Test getting current user without auth"""
        response = client.get("/api/v1/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token_xyz"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Update User Tests
    @pytest.mark.asyncio
    async def test_update_current_user_success(self, client, user_headers, test_user):
        """Test updating current user"""
        update_data = {
            "name": "Updated Name",
            "avatar_url": "https://example.com/new_avatar.jpg"
        }

        response = client.put("/api/v1/users/me", headers=user_headers, json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["avatar_url"] == "https://example.com/new_avatar.jpg"

    @pytest.mark.asyncio
    async def test_update_user_unauthorized(self, client):
        """Test updating user without auth"""
        response = client.put("/api/v1/users/me", json={"name": "Hacker"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_user_partial(self, client, user_headers):
        """Test partial user update"""
        response = client.put("/api/v1/users/me", headers=user_headers, json={
            "name": "Only Name Update"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Only Name Update"

    # Get User Balance Tests
    @pytest.mark.asyncio
    async def test_get_user_balance(self, client, user_headers, test_user):
        """Test getting user balance"""
        response = client.get("/api/v1/users/me/balance", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "balance" in data
        assert "free_generations_left" in data
        assert "free_try_ons_left" in data
        assert data["balance"] == float(test_user.balance)

    @pytest.mark.asyncio
    async def test_get_balance_unauthorized(self, client):
        """Test getting balance without auth"""
        response = client.get("/api/v1/users/me/balance")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get User Transactions Tests
    @pytest.mark.asyncio
    async def test_get_user_transactions_empty(self, client, user_headers):
        """Test getting transactions when none exist"""
        response = client.get("/api/v1/users/me/transactions", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_user_transactions_pagination(self, client, user_headers):
        """Test transaction pagination"""
        response = client.get(
            "/api/v1/users/me/transactions?skip=0&limit=10",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_get_transactions_unauthorized(self, client):
        """Test getting transactions without auth"""
        response = client.get("/api/v1/users/me/transactions")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get User History Tests
    @pytest.mark.asyncio
    async def test_get_user_history_empty(self, client, user_headers):
        """Test getting generation history when empty"""
        response = client.get("/api/v1/users/me/history", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_user_history_pagination(self, client, user_headers):
        """Test generation history pagination"""
        response = client.get(
            "/api/v1/users/me/history?skip=0&limit=20",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.asyncio
    async def test_get_history_unauthorized(self, client):
        """Test getting history without auth"""
        response = client.get("/api/v1/users/me/history")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get User Orders Tests
    @pytest.mark.asyncio
    async def test_get_user_orders_empty(self, client, user_headers):
        """Test getting orders when none exist"""
        response = client.get("/api/v1/users/me/orders", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_user_orders_with_filters(self, client, user_headers):
        """Test getting orders with filters"""
        response = client.get(
            "/api/v1/users/me/orders?order_type=purchase&status=completed",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_orders_invalid_type(self, client, user_headers):
        """Test getting orders with invalid type"""
        response = client.get(
            "/api/v1/users/me/orders?order_type=invalid",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_orders_invalid_status(self, client, user_headers):
        """Test getting orders with invalid status"""
        response = client.get(
            "/api/v1/users/me/orders?status=invalid_status",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_orders_pagination(self, client, user_headers):
        """Test orders pagination"""
        response = client.get(
            "/api/v1/users/me/orders?skip=0&limit=10",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_get_orders_unauthorized(self, client):
        """Test getting orders without auth"""
        response = client.get("/api/v1/users/me/orders")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Shop trying to access user endpoints
    @pytest.mark.asyncio
    async def test_shop_cannot_access_user_endpoint(self, client, shop_headers):
        """Test that shop cannot access user-only endpoints"""
        response = client.get("/api/v1/users/me", headers=shop_headers)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Edge cases
    @pytest.mark.asyncio
    async def test_update_user_empty_data(self, client, user_headers):
        """Test updating user with empty data"""
        response = client.put("/api/v1/users/me", headers=user_headers, json={})

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_orders_all_types(self, client, user_headers):
        """Test getting all order types"""
        # Test purchase orders
        response = client.get(
            "/api/v1/users/me/orders?order_type=purchase",
            headers=user_headers
        )
        assert response.status_code == status.HTTP_200_OK

        # Test rental orders
        response = client.get(
            "/api/v1/users/me/orders?order_type=rental",
            headers=user_headers
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_orders_all_statuses(self, client, user_headers):
        """Test getting all order statuses"""
        statuses = ["pending", "completed", "cancelled", "refunded"]
        
        for order_status in statuses:
            response = client.get(
                f"/api/v1/users/me/orders?status={order_status}",
                headers=user_headers
            )
            assert response.status_code == status.HTTP_200_OK
