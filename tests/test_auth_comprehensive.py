"""
Comprehensive Authentication Tests
Tests all authentication endpoints and scenarios
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import status


class TestAuthEndpoints:
    """Test authentication API endpoints"""

    # Google Login Tests
    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_google_login_user_success(self, mock_verify, client, db_session):
        """Test successful Google OAuth login for user"""
        mock_verify.return_value = {
            "google_id": "google_user_123",
            "email": "newuser@example.com",
            "name": "New User",
            "avatar_url": "https://example.com/avatar.jpg"
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "valid_oauth_code",
            "account_type": "user",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["account_type"] == "user"
        assert "user" in data

    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_google_login_shop_success(self, mock_verify, client, db_session):
        """Test successful Google OAuth login for shop"""
        mock_verify.return_value = {
            "google_id": "google_shop_456",
            "email": "newshop@example.com",
            "name": "New Shop"
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "valid_oauth_code",
            "account_type": "shop",
            "platform": "mobile"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["account_type"] == "shop"
        assert "shop" in data

    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_google_login_existing_user(self, mock_verify, client, db_session, test_user):
        """Test Google login with existing user"""
        mock_verify.return_value = {
            "google_id": test_user.google_id,
            "email": test_user.email,
            "name": test_user.name
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "valid_code",
            "account_type": "user",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_google_login_invalid_code(self, mock_verify, client):
        """Test Google login with invalid code"""
        mock_verify.return_value = None

        response = client.post("/api/v1/auth/google/login", json={
            "code": "invalid_code",
            "account_type": "user",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_google_login_invalid_account_type(self, client):
        """Test Google login with invalid account type"""
        response = client.post("/api/v1/auth/google/login", json={
            "code": "some_code",
            "account_type": "invalid_type",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Refresh Token Tests
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client, user_token):
        """Test successful token refresh"""
        from app.core.security import create_refresh_token
        refresh_token = create_refresh_token({"user_id": 1, "role": "user"})

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token"""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid_token_xyz"
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client):
        """Test refresh with expired token"""
        from app.core.security import create_access_token
        from datetime import timedelta
        
        # Create expired token
        expired_token = create_access_token(
            {"user_id": 1, "role": "user"},
            expires_delta=timedelta(seconds=-1)
        )

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": expired_token
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Logout Tests
    @pytest.mark.asyncio
    async def test_logout_success(self, client):
        """Test successful logout"""
        from app.core.security import create_refresh_token
        refresh_token = create_refresh_token({"user_id": 1, "role": "user"})

        response = client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, client):
        """Test logout with invalid token"""
        response = client.post("/api/v1/auth/logout", json={
            "refresh_token": "invalid_token"
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Get Google Auth URL Tests
    @pytest.mark.asyncio
    async def test_get_google_auth_url_user(self, client):
        """Test getting Google auth URL for user"""
        response = client.get("/api/v1/auth/google/url?account_type=user&platform=web")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert data["account_type"] == "user"
        assert data["platform"] == "web"

    @pytest.mark.asyncio
    async def test_get_google_auth_url_shop(self, client):
        """Test getting Google auth URL for shop"""
        response = client.get("/api/v1/auth/google/url?account_type=shop&platform=mobile")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert data["account_type"] == "shop"
        assert data["platform"] == "mobile"

    # Test Token Endpoint (Development only)
    @pytest.mark.asyncio
    async def test_create_test_token_user(self, client, db_session):
        """Test creating test token for user (dev mode)"""
        response = client.post("/api/v1/auth/test-token?account_type=user")

        # Should work in test/debug mode
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "user" in data

    @pytest.mark.asyncio
    async def test_create_test_token_shop(self, client, db_session):
        """Test creating test token for shop (dev mode)"""
        response = client.post("/api/v1/auth/test-token?account_type=shop")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "shop" in data

    @pytest.mark.asyncio
    async def test_create_test_token_admin(self, client, db_session):
        """Test creating test token for admin (dev mode)"""
        response = client.post("/api/v1/auth/test-token?account_type=admin")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"

    # Platform-specific tests
    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_google_login_mobile_platform(self, mock_verify, client):
        """Test Google login from mobile platform"""
        mock_verify.return_value = {
            "google_id": "mobile_user",
            "email": "mobile@example.com",
            "name": "Mobile User"
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "mobile_code",
            "account_type": "user",
            "platform": "mobile"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "mobile"

    @pytest.mark.asyncio
    @patch('app.core.google_auth.google_auth.verify_oauth_code')
    async def test_google_login_web_platform(self, mock_verify, client):
        """Test Google login from web platform"""
        mock_verify.return_value = {
            "google_id": "web_user",
            "email": "web@example.com",
            "name": "Web User"
        }

        response = client.post("/api/v1/auth/google/login", json={
            "code": "web_code",
            "account_type": "user",
            "platform": "web"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "web"
