"""
Tests for shop endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.shop import Shop


@pytest.mark.shop
class TestShopEndpoints:
    """Test shop endpoints"""

    @pytest.mark.anyio
    async def test_get_current_shop(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test getting current shop info"""
        response = await client.get(
            "/api/v1/shops/me",
            headers=auth_headers_shop
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_shop.email
        assert data["shop_name"] == test_shop.shop_name
        assert data["id"] == test_shop.id

    @pytest.mark.anyio
    async def test_get_current_shop_unauthorized(self, client: AsyncClient):
        """Test getting current shop without auth"""
        response = await client.get("/api/v1/shops/me")
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_update_current_shop(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test updating current shop"""
        update_data = {
            "shop_name": "Updated Shop Name",
            "description": "New shop description",
            "owner_name": "New Owner"
        }
        response = await client.put(
            "/api/v1/shops/me",
            headers=auth_headers_shop,
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["shop_name"] == "Updated Shop Name"
        assert data["description"] == "New shop description"

    @pytest.mark.anyio
    async def test_get_shop_products(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test getting shop products"""
        response = await client.get(
            "/api/v1/shops/me/products",
            headers=auth_headers_shop
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_shop_products_pagination(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test getting shop products with pagination"""
        response = await client.get(
            "/api/v1/shops/me/products?skip=0&limit=10",
            headers=auth_headers_shop
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.anyio
    async def test_get_shop_analytics(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test getting shop analytics"""
        response = await client.get(
            "/api/v1/shops/me/analytics",
            headers=auth_headers_shop
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_products" in data
        assert "active_products" in data
        assert "total_views" in data
        assert "total_try_ons" in data
        assert isinstance(data["total_products"], int)
        assert isinstance(data["active_products"], int)

    @pytest.mark.anyio
    async def test_get_shop_transactions(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test getting shop transactions"""
        response = await client.get(
            "/api/v1/shops/me/transactions",
            headers=auth_headers_shop
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_shop_transactions_pagination(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test getting shop transactions with pagination"""
        response = await client.get(
            "/api/v1/shops/me/transactions?skip=0&limit=20",
            headers=auth_headers_shop
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.anyio
    async def test_shop_cannot_access_user_endpoints(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test that shop cannot access user endpoints"""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers_shop
        )
        assert response.status_code == 401
