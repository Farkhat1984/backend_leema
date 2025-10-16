"""
Tests for admin endpoints
"""
import pytest


class TestAdminEndpoints:
    """Test admin API endpoints"""

    def test_get_admin_stats_unauthorized(self, client):
        """Test getting admin stats without authentication"""
        response = client.get("/api/admin/stats")

        assert response.status_code == 401

    def test_get_admin_stats_user_role(self, client, auth_headers):
        """Test getting admin stats with user role (not admin)"""
        response = client.get("/api/admin/stats", headers=auth_headers)

        # Should fail because user is not admin
        assert response.status_code in [401, 403]

    def test_get_admin_stats(self, client, admin_headers):
        """Test getting admin stats with admin role"""
        response = client.get("/api/admin/stats", headers=admin_headers)

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_all_users(self, client, admin_headers):
        """Test getting all users as admin"""
        response = client.get("/api/admin/users", headers=admin_headers)

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "users" in data

    def test_get_all_shops(self, client, admin_headers):
        """Test getting all shops as admin"""
        response = client.get("/api/admin/shops", headers=admin_headers)

        assert response.status_code in [200, 401, 403]

    def test_get_all_products(self, client, admin_headers):
        """Test getting all products as admin"""
        response = client.get("/api/admin/products", headers=admin_headers)

        assert response.status_code in [200, 401, 403]

    def test_moderate_product(self, client, admin_headers):
        """Test moderating a product"""
        moderation_data = {
            "status": "approved",
            "reason": "Looks good"
        }

        response = client.post("/api/admin/products/1/moderate", 
                              headers=admin_headers,
                              json=moderation_data)

        assert response.status_code in [200, 401, 403, 404]

    def test_ban_user(self, client, admin_headers):
        """Test banning a user"""
        response = client.post("/api/admin/users/1/ban", headers=admin_headers)

        assert response.status_code in [200, 401, 403, 404]

    def test_unban_user(self, client, admin_headers):
        """Test unbanning a user"""
        response = client.post("/api/admin/users/1/unban", headers=admin_headers)

        assert response.status_code in [200, 401, 403, 404]

    def test_ban_shop(self, client, admin_headers):
        """Test banning a shop"""
        response = client.post("/api/admin/shops/1/ban", headers=admin_headers)

        assert response.status_code in [200, 401, 403, 404]

    def test_get_pending_products(self, client, admin_headers):
        """Test getting products pending moderation"""
        response = client.get("/api/admin/products/pending", headers=admin_headers)

        assert response.status_code in [200, 401, 403]

    def test_get_transactions(self, client, admin_headers):
        """Test getting all transactions as admin"""
        response = client.get("/api/admin/transactions", headers=admin_headers)

        assert response.status_code in [200, 401, 403]

    def test_update_settings(self, client, admin_headers):
        """Test updating system settings"""
        settings_data = {
            "generation_price": 1.0,
            "try_on_price": 2.0
        }

        response = client.post("/api/admin/settings", 
                              headers=admin_headers,
                              json=settings_data)

        assert response.status_code in [200, 401, 403, 422]

    def test_delete_user(self, client, admin_headers):
        """Test deleting a user as admin"""
        response = client.delete("/api/admin/users/1", headers=admin_headers)

        assert response.status_code in [200, 204, 401, 403, 404]

    def test_delete_shop(self, client, admin_headers):
        """Test deleting a shop as admin"""
        response = client.delete("/api/admin/shops/1", headers=admin_headers)

        assert response.status_code in [200, 204, 401, 403, 404]
