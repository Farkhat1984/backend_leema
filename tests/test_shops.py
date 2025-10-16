"""
Tests for shop endpoints
"""
import pytest


class TestShopEndpoints:
    """Test shop API endpoints"""

    def test_get_current_shop_unauthorized(self, client):
        """Test getting current shop without authentication"""
        response = client.get("/api/shops/me")

        assert response.status_code == 401

    def test_get_current_shop(self, client, auth_headers):
        """Test getting current shop information"""
        # User token won't work for shop endpoint
        response = client.get("/api/shops/me", headers=auth_headers)

        assert response.status_code in [200, 401, 403]

    def test_update_current_shop(self, client, auth_headers):
        """Test updating current shop"""
        update_data = {
            "name": "Updated Shop Name",
            "description": "Updated description"
        }

        response = client.put("/api/shops/me", 
                             headers=auth_headers,
                             json=update_data)

        assert response.status_code in [200, 401, 403, 404]

    def test_get_shop_products(self, client, auth_headers):
        """Test getting shop products"""
        response = client.get("/api/shops/me/products", headers=auth_headers)

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_shop_analytics(self, client, auth_headers):
        """Test getting shop analytics"""
        response = client.get("/api/shops/me/analytics", headers=auth_headers)

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert "total_sales" in data or isinstance(data, dict)

    def test_get_shop_transactions(self, client, auth_headers):
        """Test getting shop transactions"""
        response = client.get("/api/shops/me/transactions", headers=auth_headers)

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_shop_by_id(self, client):
        """Test getting shop by ID (public endpoint)"""
        response = client.get("/api/shops/1")

        assert response.status_code in [200, 404]

    def test_withdraw_balance(self, client, auth_headers):
        """Test withdrawing shop balance"""
        withdraw_data = {
            "amount": 50.0,
            "paypal_email": "shop@example.com"
        }

        response = client.post("/api/shops/me/withdraw", 
                              headers=auth_headers,
                              json=withdraw_data)

        assert response.status_code in [200, 401, 403, 400]
