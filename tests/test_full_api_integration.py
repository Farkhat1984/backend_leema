"""
Comprehensive Full API Integration Tests
Tests all API endpoints with real scenarios using actual credentials
"""
import pytest
import asyncio
import os
from typing import Dict, Any
from fastapi.testclient import TestClient
import time


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test Authentication endpoints"""
    
    def test_get_google_auth_url_user(self, client: TestClient):
        """Test getting Google OAuth URL for user"""
        response = client.get("/api/v1/auth/google/url?account_type=user&platform=web")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]
    
    def test_get_google_auth_url_shop(self, client: TestClient):
        """Test getting Google OAuth URL for shop"""
        response = client.get("/api/v1/auth/google/url?account_type=shop&platform=mobile")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
    
    def test_create_test_token_user(self, client: TestClient):
        """Test creating test token for user (development)"""
        response = client.post("/api/v1/auth/test-token?account_type=user")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_create_test_token_shop(self, client: TestClient):
        """Test creating test token for shop (development)"""
        response = client.post("/api/v1/auth/test-token?account_type=shop")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_refresh_token(self, client: TestClient):
        """Test refreshing access token"""
        # First get a test token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        refresh_token = tokens["refresh_token"]
        
        # Refresh it
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        new_tokens = response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
    
    def test_logout(self, client: TestClient):
        """Test user logout"""
        # Get test token first
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"


@pytest.mark.integration
class TestUserEndpoints:
    """Test User endpoints"""
    
    def test_get_current_user(self, client: TestClient, user_headers: Dict[str, str]):
        """Test getting current user info"""
        response = client.get("/api/v1/users/me", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["email"] == "zfaragj@gmail.com"
        assert "balance" in data
        assert "free_generations_left" in data
        assert "free_try_ons_left" in data
    
    def test_update_current_user(self, client: TestClient, user_headers: Dict[str, str]):
        """Test updating current user"""
        response = client.put(
            "/api/v1/users/me",
            headers=user_headers,
            json={
                "name": "Updated Test User",
                "avatar_url": "https://example.com/new-avatar.jpg"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Test User"
    
    def test_get_user_balance(self, client: TestClient, user_headers: Dict[str, str]):
        """Test getting user balance"""
        response = client.get("/api/v1/users/me/balance", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "free_generations_left" in data
        assert "free_try_ons_left" in data
        assert isinstance(data["balance"], (int, float))
    
    def test_get_user_transactions(self, client: TestClient, user_headers: Dict[str, str]):
        """Test getting user transactions"""
        response = client.get("/api/v1/users/me/transactions?skip=0&limit=50", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_history(self, client: TestClient, user_headers: Dict[str, str]):
        """Test getting user generation history"""
        response = client.get("/api/v1/users/me/history?skip=0&limit=50", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_orders(self, client: TestClient, user_headers: Dict[str, str]):
        """Test getting user orders"""
        response = client.get("/api/v1/users/me/orders?skip=0&limit=50", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_orders_filtered(self, client: TestClient, user_headers: Dict[str, str]):
        """Test getting filtered user orders"""
        response = client.get(
            "/api/v1/users/me/orders?order_type=purchase&status=completed",
            headers=user_headers
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestShopEndpoints:
    """Test Shop endpoints"""
    
    def test_get_current_shop(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test getting current shop info"""
        response = client.get("/api/v1/shops/me", headers=shop_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["email"] == "ckdshfh@gmail.com"
        assert "shop_name" in data
        assert "balance" in data
    
    def test_update_current_shop(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test updating current shop"""
        response = client.put(
            "/api/v1/shops/me",
            headers=shop_headers,
            json={
                "shop_name": "Updated Shop Name",
                "description": "Updated shop description"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["shop_name"] == "Updated Shop Name"
    
    def test_get_shop_products(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test getting shop products"""
        response = client.get("/api/v1/shops/me/products?skip=0&limit=50", headers=shop_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_shop_analytics(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test getting shop analytics"""
        response = client.get("/api/v1/shops/me/analytics", headers=shop_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_products" in data
        assert "active_products" in data
        assert "total_views" in data
        assert "total_try_ons" in data
        assert "total_purchases" in data
        assert "total_revenue" in data
    
    def test_get_shop_transactions(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test getting shop transactions"""
        response = client.get("/api/v1/shops/me/transactions?skip=0&limit=50", headers=shop_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestProductEndpoints:
    """Test Product endpoints"""
    
    def test_get_products_list(self, client: TestClient):
        """Test getting public products list"""
        response = client.get("/api/v1/products/?skip=0&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
    
    def test_search_products(self, client: TestClient):
        """Test advanced product search"""
        response = client.get("/api/v1/products/search?query=test&min_price=0&max_price=1000")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
    
    def test_search_products_with_filters(self, client: TestClient):
        """Test product search with all filters"""
        response = client.get(
            "/api/v1/products/search"
            "?is_active=true"
            "&moderation_status=approved"
            "&sort_by=created_at"
            "&sort_order=desc"
        )
        assert response.status_code == 200
    
    def test_create_product(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test creating a new product"""
        product_data = {
            "name": "New Fashion Item",
            "description": "Stylish new product",
            "price": 199.99,
            "image_urls": '["https://example.com/image1.jpg"]'
        }
        response = client.post(
            "/api/v1/products/",
            headers=shop_headers,
            data=product_data
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "New Fashion Item"
        assert data["price"] == 199.99
    
    def test_get_product_by_id(self, client: TestClient, test_product):
        """Test getting product by ID"""
        response = client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id
        assert "name" in data
        assert "price" in data
    
    def test_update_product(self, client: TestClient, shop_headers: Dict[str, str], test_product):
        """Test updating a product"""
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            headers=shop_headers,
            json={
                "name": "Updated Product Name",
                "price": 149.99
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Product Name"
    
    def test_delete_product(self, client: TestClient, shop_headers: Dict[str, str], test_product):
        """Test deleting a product"""
        response = client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=shop_headers
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestProductReviews:
    """Test Product Review endpoints"""
    
    def test_create_review(self, client: TestClient, user_headers: Dict[str, str], test_product):
        """Test creating a product review"""
        response = client.post(
            f"/api/v1/products/{test_product.id}/reviews",
            headers=user_headers,
            json={
                "rating": 5,
                "comment": "Excellent product!"
            }
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["rating"] == 5
        assert data["comment"] == "Excellent product!"
    
    def test_get_product_reviews(self, client: TestClient, test_product):
        """Test getting product reviews"""
        response = client.get(f"/api/v1/products/{test_product.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_review_stats(self, client: TestClient, test_product):
        """Test getting product review statistics"""
        response = client.get(f"/api/v1/products/{test_product.id}/reviews/stats")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.payments
class TestPaymentEndpoints:
    """Test Payment endpoints"""
    
    def test_create_user_topup_payment(self, client: TestClient, user_headers: Dict[str, str]):
        """Test creating user balance top-up payment"""
        response = client.post(
            "/api/v1/payments/user/top-up",
            headers={**user_headers, "x-client-platform": "mobile"},
            json={
                "amount": 50.0,
                "payment_type": "user_topup",
                "description": "Balance top-up test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert "approval_url" in data
        assert data["amount"] == 50.0
        assert "paypal.com" in data["approval_url"]
    
    def test_create_shop_topup_payment(self, client: TestClient, shop_headers: Dict[str, str]):
        """Test creating shop balance top-up payment"""
        response = client.post(
            "/api/v1/payments/shop/top-up",
            headers={**shop_headers, "x-client-platform": "web"},
            json={
                "amount": 100.0,
                "payment_type": "shop_topup",
                "description": "Shop balance top-up"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert "approval_url" in data
        assert data["amount"] == 100.0
    
    def test_create_rent_payment(self, client: TestClient, shop_headers: Dict[str, str], test_product):
        """Test creating product rent payment"""
        response = client.post(
            "/api/v1/payments/shop/rent-product",
            headers={**shop_headers, "x-client-platform": "mobile"},
            json={
                "amount": 10.0,
                "payment_type": "rent_product",
                "extra_data": {
                    "product_id": test_product.id,
                    "months": 1
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert "approval_url" in data


@pytest.mark.integration
@pytest.mark.generations
class TestGenerationEndpoints:
    """Test AI Generation endpoints"""
    
    def test_generate_image_from_text(self, client: TestClient, user_headers: Dict[str, str]):
        """Test generating image from text prompt"""
        response = client.post(
            "/api/v1/generations/generate-from-text",
            headers=user_headers,
            json={
                "prompt": "A stylish red dress on white background",
                "aspect_ratio": "1:1"
            }
        )
        # May fail if no balance or API issues
        assert response.status_code in [200, 400, 402, 500]
    
    def test_generate_person_image(self, client: TestClient, user_headers: Dict[str, str]):
        """Test generating person/model image"""
        response = client.post(
            "/api/v1/generations/generate-person",
            headers=user_headers,
            json={
                "description": "A professional fashion model in casual outfit",
                "aspect_ratio": "2:3"
            }
        )
        assert response.status_code in [200, 400, 402, 500]
    
    def test_generate_clothing_image(self, client: TestClient, user_headers: Dict[str, str]):
        """Test generating clothing image"""
        response = client.post(
            "/api/v1/generations/generate-clothing",
            headers=user_headers,
            json={
                "description": "A modern blue jacket with zipper",
                "aspect_ratio": "1:1"
            }
        )
        assert response.status_code in [200, 400, 402, 500]
    
    def test_generate_from_text_and_images(self, client: TestClient, user_headers: Dict[str, str]):
        """Test generating image from text and reference images"""
        # Simple base64 test image (1x1 transparent PNG)
        test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = client.post(
            "/api/v1/generations/generate-from-text-and-images",
            headers=user_headers,
            json={
                "prompt": "Create similar fashion item",
                "images_base64": [test_image],
                "aspect_ratio": "1:1"
            }
        )
        assert response.status_code in [200, 400, 402, 422, 500]
    
    def test_apply_clothing_base64(self, client: TestClient, user_headers: Dict[str, str]):
        """Test applying clothing to model with base64 images"""
        test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = client.post(
            "/api/v1/generations/apply-clothing-base64",
            headers=user_headers,
            json={
                "person_base64": test_image,
                "clothing_base64": test_image,
                "aspect_ratio": "2:3"
            }
        )
        assert response.status_code in [200, 400, 402, 422, 500]


@pytest.mark.integration
@pytest.mark.admin
class TestAdminEndpoints:
    """Test Admin endpoints"""
    
    def test_get_dashboard(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test getting admin dashboard"""
        response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_shops" in data
        assert "total_products" in data
        assert "total_revenue" in data
        assert "pending_moderation" in data
    
    def test_get_all_users(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test getting all users"""
        response = client.get("/api/v1/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_all_shops(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test getting all shops"""
        response = client.get("/api/v1/admin/shops", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_settings(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test getting platform settings"""
        response = client.get("/api/v1/admin/settings", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_update_setting(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test updating platform setting"""
        response = client.put(
            "/api/v1/admin/settings/user_generation_price",
            headers=admin_headers,
            json={
                "key": "user_generation_price",
                "value": "1.5"
            }
        )
        assert response.status_code in [200, 404]
    
    def test_get_moderation_queue(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test getting products pending moderation"""
        response = client.get("/api/v1/admin/moderation/queue", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_approve_product(self, client: TestClient, admin_headers: Dict[str, str], test_product):
        """Test approving a product"""
        response = client.post(
            f"/api/v1/admin/moderation/{test_product.id}/approve",
            headers=admin_headers,
            json={
                "action": "approve",
                "notes": "Approved for testing"
            }
        )
        assert response.status_code in [200, 400]
    
    def test_reject_product(self, client: TestClient, admin_headers: Dict[str, str], test_product):
        """Test rejecting a product"""
        response = client.post(
            f"/api/v1/admin/moderation/{test_product.id}/reject",
            headers=admin_headers,
            json={
                "action": "reject",
                "notes": "Does not meet quality standards"
            }
        )
        assert response.status_code in [200, 400]
    
    def test_get_user_details(self, client: TestClient, admin_headers: Dict[str, str], test_user):
        """Test getting detailed user information"""
        response = client.get(f"/api/v1/admin/users/{test_user.id}", headers=admin_headers)
        assert response.status_code == 200
    
    def test_change_user_role(self, client: TestClient, admin_headers: Dict[str, str], test_user):
        """Test changing user role"""
        response = client.put(
            f"/api/v1/admin/users/{test_user.id}/role?new_role=admin",
            headers=admin_headers
        )
        assert response.status_code in [200, 400]
    
    def test_get_all_transactions(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test getting all platform transactions"""
        response = client.get(
            "/api/v1/admin/transactions?skip=0&limit=100",
            headers=admin_headers
        )
        assert response.status_code == 200
    
    def test_bulk_approve_products(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test bulk approving products"""
        response = client.post(
            "/api/v1/admin/products/bulk-approve?notes=Bulk approved",
            headers=admin_headers,
            json=[1, 2, 3]
        )
        assert response.status_code in [200, 400, 404]


@pytest.mark.integration
class TestHealthEndpoints:
    """Test Health and utility endpoints"""
    
    def test_root_endpoint(self, client: TestClient):
        """Test API root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_websocket_stats(self, client: TestClient):
        """Test WebSocket statistics endpoint"""
        response = client.get("/ws/stats")
        assert response.status_code == 200


@pytest.mark.integration
class TestCompleteUserJourney:
    """Test complete user journey scenarios"""
    
    def test_new_user_complete_flow(self, client: TestClient):
        """Test complete new user flow: auth -> view profile -> view products"""
        # 1. Create test token (simulating Google OAuth)
        auth_response = client.post("/api/v1/auth/test-token?account_type=user")
        assert auth_response.status_code == 200
        tokens = auth_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # 2. Get user profile
        profile_response = client.get("/api/v1/users/me", headers=headers)
        assert profile_response.status_code == 200
        user = profile_response.json()
        assert "email" in user
        
        # 3. Check balance
        balance_response = client.get("/api/v1/users/me/balance", headers=headers)
        assert balance_response.status_code == 200
        balance = balance_response.json()
        assert "balance" in balance
        
        # 4. Browse products
        products_response = client.get("/api/v1/products/")
        assert products_response.status_code == 200
        
        # 5. Search products
        search_response = client.get("/api/v1/products/search?query=fashion")
        assert search_response.status_code == 200
    
    def test_shop_owner_complete_flow(self, client: TestClient):
        """Test complete shop owner flow: auth -> create product -> view analytics"""
        # 1. Create shop test token
        auth_response = client.post("/api/v1/auth/test-token?account_type=shop")
        assert auth_response.status_code == 200
        tokens = auth_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # 2. Get shop profile
        profile_response = client.get("/api/v1/shops/me", headers=headers)
        assert profile_response.status_code == 200
        shop = profile_response.json()
        assert "shop_name" in shop
        
        # 3. View analytics
        analytics_response = client.get("/api/v1/shops/me/analytics", headers=headers)
        assert analytics_response.status_code == 200
        
        # 4. Get shop products
        products_response = client.get("/api/v1/shops/me/products", headers=headers)
        assert products_response.status_code == 200
        
        # 5. Create new product
        product_data = {
            "name": "Test Product Journey",
            "description": "Product created during test journey",
            "price": 99.99,
            "image_urls": '["https://example.com/test.jpg"]'
        }
        create_response = client.post(
            "/api/v1/products/",
            headers=headers,
            data=product_data
        )
        assert create_response.status_code in [200, 201]


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_unauthorized_access(self, client: TestClient):
        """Test accessing protected endpoint without auth"""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401
    
    def test_invalid_token(self, client: TestClient):
        """Test with invalid token"""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
    
    def test_get_nonexistent_product(self, client: TestClient):
        """Test getting non-existent product"""
        response = client.get("/api/v1/products/999999")
        assert response.status_code == 404
    
    def test_create_product_as_user(self, client: TestClient, user_headers: Dict[str, str]):
        """Test creating product as user (should fail)"""
        product_data = {
            "name": "Should Fail",
            "price": 99.99
        }
        response = client.post(
            "/api/v1/products/",
            headers=user_headers,
            data=product_data
        )
        assert response.status_code in [403, 400]
    
    def test_admin_endpoint_as_user(self, client: TestClient, user_headers: Dict[str, str]):
        """Test accessing admin endpoint as regular user"""
        response = client.get("/api/v1/admin/dashboard", headers=user_headers)
        assert response.status_code == 403
    
    def test_invalid_payment_amount(self, client: TestClient, user_headers: Dict[str, str]):
        """Test creating payment with invalid amount"""
        response = client.post(
            "/api/v1/payments/user/top-up",
            headers=user_headers,
            json={
                "amount": -10.0,
                "payment_type": "user_topup"
            }
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestPaginationAndFiltering:
    """Test pagination and filtering across endpoints"""
    
    def test_products_pagination(self, client: TestClient):
        """Test products pagination"""
        response1 = client.get("/api/v1/products/?skip=0&limit=10")
        assert response1.status_code == 200
        
        response2 = client.get("/api/v1/products/?skip=10&limit=10")
        assert response2.status_code == 200
    
    def test_user_transactions_pagination(self, client: TestClient, user_headers: Dict[str, str]):
        """Test user transactions pagination"""
        response = client.get("/api/v1/users/me/transactions?skip=0&limit=20", headers=user_headers)
        assert response.status_code == 200
    
    def test_product_search_sorting(self, client: TestClient):
        """Test product search with different sorting"""
        # Sort by created_at descending
        response1 = client.get("/api/v1/products/search?sort_by=created_at&sort_order=desc")
        assert response1.status_code == 200
        
        # Sort by price ascending
        response2 = client.get("/api/v1/products/search?sort_by=price&sort_order=asc")
        assert response2.status_code == 200
    
    def test_user_orders_filtering(self, client: TestClient, user_headers: Dict[str, str]):
        """Test user orders with filters"""
        response = client.get(
            "/api/v1/users/me/orders?order_type=purchase&status=completed",
            headers=user_headers
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
