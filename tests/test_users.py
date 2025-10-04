"""
Tests for user endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


@pytest.mark.user
class TestUserEndpoints:
    """Test user endpoints"""

    @pytest.mark.anyio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test getting current user info"""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers_user
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["id"] == test_user.id

    @pytest.mark.anyio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without auth"""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_update_current_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test updating current user"""
        update_data = {
            "name": "Updated Name",
            "avatar_url": "https://example.com/avatar.jpg"
        }
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers_user,
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"

    @pytest.mark.anyio
    async def test_get_user_balance(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test getting user balance"""
        response = await client.get(
            "/api/v1/users/me/balance",
            headers=auth_headers_user
        )
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "free_generations_left" in data
        assert "free_try_ons_left" in data
        assert isinstance(data["balance"], (int, float))
        assert isinstance(data["free_generations_left"], int)
        assert isinstance(data["free_try_ons_left"], int)

    @pytest.mark.anyio
    async def test_get_user_transactions(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test getting user transactions"""
        response = await client.get(
            "/api/v1/users/me/transactions",
            headers=auth_headers_user
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_user_transactions_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test getting user transactions with pagination"""
        response = await client.get(
            "/api/v1/users/me/transactions?skip=0&limit=10",
            headers=auth_headers_user
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.anyio
    async def test_get_user_generation_history(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test getting user generation history"""
        response = await client.get(
            "/api/v1/users/me/history",
            headers=auth_headers_user
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_user_generation_history_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test getting user generation history with pagination"""
        response = await client.get(
            "/api/v1/users/me/history?skip=0&limit=20",
            headers=auth_headers_user
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.anyio
    async def test_update_user_invalid_data(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test updating user with invalid data"""
        update_data = {
            "email": "invalid-email"  # Email cannot be updated
        }
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers_user,
            json=update_data
        )
        # Should either ignore email or return success
        # (depending on schema validation)
        assert response.status_code in [200, 422]
