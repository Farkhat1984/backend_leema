"""
Comprehensive Shop Tests
Tests all shop endpoints and scenarios
"""
import pytest
from fastapi import status


class TestShopEndpoints:
    """Test shop API endpoints"""

    # Get Current Shop Tests
    @pytest.mark.asyncio
    async def test_get_current_shop_success(self, client, shop_headers, test_shop):
        """Test getting current shop info"""
        response = client.get("/api/v1/shops/me", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_shop.email
        assert data["shop_name"] == test_shop.shop_name
        assert "balance" in data

    @pytest.mark.asyncio
    async def test_get_current_shop_unauthorized(self, client):
        """Test getting shop info without auth"""
        response = client.get("/api/v1/shops/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_user_cannot_access_shop_endpoint(self, client, user_headers):
        """Test that user cannot access shop-only endpoints"""
        response = client.get("/api/v1/shops/me", headers=user_headers)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Update Shop Tests
    @pytest.mark.asyncio
    async def test_update_current_shop_success(self, client, shop_headers, test_shop):
        """Test updating current shop"""
        update_data = {
            "shop_name": "Updated Shop Name",
            "owner_name": "New Owner",
            "description": "Updated description",
            "address": "123 New Street",
            "phone": "+1234567890"
        }

        response = client.put("/api/v1/shops/me", headers=shop_headers, json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["shop_name"] == "Updated Shop Name"
        assert data["owner_name"] == "New Owner"

    @pytest.mark.asyncio
    async def test_update_shop_partial(self, client, shop_headers):
        """Test partial shop update"""
        response = client.put("/api/v1/shops/me", headers=shop_headers, json={
            "description": "New description only"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "New description only"

    @pytest.mark.asyncio
    async def test_update_shop_unauthorized(self, client):
        """Test updating shop without auth"""
        response = client.put("/api/v1/shops/me", json={"shop_name": "Hacked"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get Shop Products Tests
    @pytest.mark.asyncio
    async def test_get_shop_products_empty(self, client, shop_headers):
        """Test getting shop products when none exist"""
        response = client.get("/api/v1/shops/me/products", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_shop_products_with_product(self, client, shop_headers, test_product):
        """Test getting shop products"""
        response = client.get("/api/v1/shops/me/products", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_shop_products_pagination(self, client, shop_headers):
        """Test shop products pagination"""
        response = client.get(
            "/api/v1/shops/me/products?skip=0&limit=10",
            headers=shop_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_get_products_unauthorized(self, client):
        """Test getting products without auth"""
        response = client.get("/api/v1/shops/me/products")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get Shop Analytics Tests
    @pytest.mark.asyncio
    async def test_get_shop_analytics(self, client, shop_headers):
        """Test getting shop analytics"""
        response = client.get("/api/v1/shops/me/analytics", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_products" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_analytics_unauthorized(self, client):
        """Test getting analytics without auth"""
        response = client.get("/api/v1/shops/me/analytics")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get Shop Transactions Tests
    @pytest.mark.asyncio
    async def test_get_shop_transactions_empty(self, client, shop_headers):
        """Test getting shop transactions when none exist"""
        response = client.get("/api/v1/shops/me/transactions", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_shop_transactions_pagination(self, client, shop_headers):
        """Test shop transactions pagination"""
        response = client.get(
            "/api/v1/shops/me/transactions?skip=0&limit=20",
            headers=shop_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.asyncio
    async def test_get_shop_transactions_unauthorized(self, client):
        """Test getting transactions without auth"""
        response = client.get("/api/v1/shops/me/transactions")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Edge Cases
    @pytest.mark.asyncio
    async def test_update_shop_with_empty_data(self, client, shop_headers):
        """Test updating shop with empty data"""
        response = client.put("/api/v1/shops/me", headers=shop_headers, json={})

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_products_with_large_limit(self, client, shop_headers):
        """Test getting products with large limit"""
        response = client.get(
            "/api/v1/shops/me/products?skip=0&limit=100",
            headers=shop_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 100

    @pytest.mark.asyncio
    async def test_update_shop_invalid_data(self, client, shop_headers):
        """Test updating shop with invalid data types"""
        response = client.put("/api/v1/shops/me", headers=shop_headers, json={
            "balance": "not_a_number"  # Should be rejected or handled
        })

        # Should either accept (ignore invalid field) or reject
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @pytest.mark.asyncio
    async def test_shop_analytics_structure(self, client, shop_headers):
        """Test shop analytics response structure"""
        response = client.get("/api/v1/shops/me/analytics", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Analytics should be a dictionary
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_multiple_shops_isolation(self, client, shop_headers, db_session):
        """Test that shops can only access their own data"""
        # Create another shop
        from app.services.shop_service import shop_service
        from app.schemas.shop import ShopCreate
        
        other_shop_data = ShopCreate(
            google_id="other_shop_google",
            email="othershop@example.com",
            shop_name="Other Shop",
            owner_name="Other Owner"
        )
        other_shop = await shop_service.create(db_session, other_shop_data)

        # Original shop should not see other shop's data
        response = client.get("/api/v1/shops/me", headers=shop_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] != "othershop@example.com"
