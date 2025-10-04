"""
Tests for admin endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.shop import Shop
from app.models.product import Product
from unittest.mock import patch


@pytest.mark.admin
class TestAdminEndpoints:
    """Test admin endpoints"""

    @pytest.mark.anyio
    async def test_get_dashboard(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict
    ):
        """Test getting admin dashboard"""
        response = await client.get(
            "/api/v1/admin/dashboard",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_shops" in data
        assert "total_products" in data
        assert "active_products" in data
        assert "total_generations" in data
        assert "total_revenue" in data
        assert "pending_moderation" in data
        assert "pending_refunds" in data

    @pytest.mark.anyio
    async def test_get_dashboard_unauthorized(
        self,
        client: AsyncClient,
        auth_headers_user: dict
    ):
        """Test getting dashboard without admin role"""
        response = await client.get(
            "/api/v1/admin/dashboard",
            headers=auth_headers_user
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_get_settings(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict
    ):
        """Test getting platform settings"""
        response = await client.get(
            "/api/v1/admin/settings",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_update_setting(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict,
        db_session: AsyncSession
    ):
        """Test updating platform setting"""
        # First, initialize a setting
        from app.services.settings_service import settings_service
        await settings_service.set_setting(
            db_session,
            "user_generation_price",
            "1.0",
            "Price for generation"
        )

        setting_data = {
            "key": "user_generation_price",
            "value": "2.0",
            "description": "Updated price"
        }
        response = await client.put(
            "/api/v1/admin/settings/user_generation_price",
            headers=auth_headers_admin,
            json=setting_data
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_get_moderation_queue(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict
    ):
        """Test getting moderation queue"""
        response = await client.get(
            "/api/v1/admin/moderation/queue",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_approve_product(
        self,
        client: AsyncClient,
        test_admin: User,
        test_product: Product,
        test_shop,
        auth_headers_admin: dict,
        db_session: AsyncSession
    ):
        """Test approving product"""
        # Set product to pending moderation and ensure shop has balance
        test_product.moderation_status = "pending"
        test_product.shop_id = test_shop.id

        # Add balance to shop for approval fee (default is $5)
        test_shop.balance = 100.0

        await db_session.commit()

        with patch('app.core.email.email_service.send_product_approved_notification'):
            action_data = {
                "action": "approve",
                "notes": "Looks good"
            }
            response = await client.post(
                f"/api/v1/admin/moderation/{test_product.id}/approve",
                headers=auth_headers_admin,
                json=action_data
            )
            assert response.status_code == 200

    @pytest.mark.anyio
    async def test_reject_product(
        self,
        client: AsyncClient,
        test_admin: User,
        test_product: Product,
        auth_headers_admin: dict,
        db_session: AsyncSession
    ):
        """Test rejecting product"""
        # Set product to pending moderation
        test_product.moderation_status = "pending"
        await db_session.commit()

        with patch('app.core.email.email_service.send_product_rejected_notification'):
            action_data = {
                "action": "reject",
                "notes": "Violates guidelines"
            }
            response = await client.post(
                f"/api/v1/admin/moderation/{test_product.id}/reject",
                headers=auth_headers_admin,
                json=action_data
            )
            assert response.status_code == 200

    @pytest.mark.anyio
    async def test_reject_product_without_notes(
        self,
        client: AsyncClient,
        test_admin: User,
        test_product: Product,
        auth_headers_admin: dict
    ):
        """Test rejecting product without notes"""
        action_data = {
            "action": "reject",
            "notes": None
        }
        response = await client.post(
            f"/api/v1/admin/moderation/{test_product.id}/reject",
            headers=auth_headers_admin,
            json=action_data
        )
        assert response.status_code in [400, 422]

    @pytest.mark.anyio
    async def test_get_refund_requests(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict
    ):
        """Test getting refund requests"""
        response = await client.get(
            "/api/v1/admin/refunds",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_refund_requests_filtered(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict
    ):
        """Test getting refund requests with status filter"""
        response = await client.get(
            "/api/v1/admin/refunds?status=pending",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_process_refund_approve(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict,
        db_session: AsyncSession
    ):
        """Test approving refund request"""
        # Create a refund request
        from app.models.refund import Refund, RefundStatus

        refund = Refund(
            transaction_id=1,
            user_id=1,
            reason="Changed my mind",
            status=RefundStatus.REQUESTED
        )
        db_session.add(refund)
        await db_session.commit()
        await db_session.refresh(refund)

        action_data = {
            "action": "approve",
            "admin_notes": "Approved for refund"
        }
        response = await client.post(
            f"/api/v1/admin/refunds/{refund.id}/process",
            headers=auth_headers_admin,
            json=action_data
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_process_refund_reject(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict,
        db_session: AsyncSession
    ):
        """Test rejecting refund request"""
        from app.models.refund import Refund, RefundStatus

        refund = Refund(
            transaction_id=1,
            user_id=1,
            reason="Test reason",
            status=RefundStatus.REQUESTED
        )
        db_session.add(refund)
        await db_session.commit()
        await db_session.refresh(refund)

        action_data = {
            "action": "reject",
            "admin_notes": "Outside refund period"
        }
        response = await client.post(
            f"/api/v1/admin/refunds/{refund.id}/process",
            headers=auth_headers_admin,
            json=action_data
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_process_refund_not_found(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers_admin: dict
    ):
        """Test processing non-existent refund"""
        action_data = {
            "action": "approve",
            "admin_notes": "Test"
        }
        response = await client.post(
            "/api/v1/admin/refunds/99999/process",
            headers=auth_headers_admin,
            json=action_data
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_get_all_users(
        self,
        client: AsyncClient,
        test_admin: User,
        test_user: User,
        auth_headers_admin: dict
    ):
        """Test getting all users list"""
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least test_admin and test_user
        assert len(data) >= 2

    @pytest.mark.anyio
    async def test_get_all_users_unauthorized(
        self,
        client: AsyncClient,
        auth_headers_user: dict
    ):
        """Test that regular user cannot get all users"""
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers_user
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_get_all_shops(
        self,
        client: AsyncClient,
        test_admin: User,
        test_shop: Shop,
        auth_headers_admin: dict
    ):
        """Test getting all shops list"""
        response = await client.get(
            "/api/v1/admin/shops",
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least test_shop
        assert len(data) >= 1

    @pytest.mark.anyio
    async def test_get_all_shops_unauthorized(
        self,
        client: AsyncClient,
        auth_headers_user: dict
    ):
        """Test that regular user cannot get all shops"""
        response = await client.get(
            "/api/v1/admin/shops",
            headers=auth_headers_user
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_non_admin_cannot_access(
        self,
        client: AsyncClient,
        auth_headers_user: dict
    ):
        """Test that regular user cannot access admin endpoints"""
        endpoints = [
            "/api/v1/admin/dashboard",
            "/api/v1/admin/settings",
            "/api/v1/admin/moderation/queue",
            "/api/v1/admin/refunds",
            "/api/v1/admin/users",
            "/api/v1/admin/shops"
        ]

        for endpoint in endpoints:
            response = await client.get(
                endpoint,
                headers=auth_headers_user
            )
            assert response.status_code == 403
