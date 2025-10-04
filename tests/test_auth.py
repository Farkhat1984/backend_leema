"""
Tests for authentication endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.auth
class TestAuthEndpoints:
    """Test authentication endpoints"""

    @pytest.mark.anyio
    async def test_get_google_auth_url(self, client: AsyncClient):
        """Test getting Google OAuth URL"""
        response = await client.get("/api/v1/auth/google/url?account_type=user")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]

    @pytest.mark.anyio
    async def test_get_google_auth_url_shop(self, client: AsyncClient):
        """Test getting Google OAuth URL for shop"""
        response = await client.get("/api/v1/auth/google/url?account_type=shop")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data

    @pytest.mark.anyio
    async def test_create_test_token_user(self, client: AsyncClient):
        """Test creating test token for user"""
        response = await client.post("/api/v1/auth/test-token?account_type=user")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"

    @pytest.mark.anyio
    async def test_create_test_token_shop(self, client: AsyncClient):
        """Test creating test token for shop"""
        response = await client.post("/api/v1/auth/test-token?account_type=shop")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "shop" in data
        assert data["shop"]["email"] == "testshop@example.com"

    @pytest.mark.anyio
    async def test_create_test_token_admin(self, client: AsyncClient):
        """Test creating test token for admin"""
        response = await client.post("/api/v1/auth/test-token?account_type=admin")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"

    @pytest.mark.anyio
    async def test_refresh_token(self, client: AsyncClient, user_token: str):
        """Test refreshing access token"""
        from app.core.security import create_refresh_token

        refresh_token = create_refresh_token({"user_id": 1, "role": "user"})

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.anyio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refreshing with invalid token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_google_login_invalid_code(self, client: AsyncClient):
        """Test Google login with invalid code"""
        response = await client.post(
            "/api/v1/auth/google/login",
            json={
                "code": "invalid_code_123",
                "account_type": "user"
            }
        )
        # Should fail because code is invalid
        assert response.status_code in [401, 400, 500]

    @pytest.mark.anyio
    async def test_google_login_invalid_account_type(self, client: AsyncClient):
        """Test Google login with invalid account type"""
        response = await client.post(
            "/api/v1/auth/google/login",
            json={
                "code": "some_code",
                "account_type": "invalid"
            }
        )
        # Pydantic validation should return 422 for invalid enum value
        assert response.status_code == 422
