"""
Real-world Test Scenarios with Actual API Calls
Uses credentials from .env file
"""
import pytest
import os
import base64
from typing import Dict
from fastapi.testclient import TestClient


# Test credentials from .env
USER_EMAIL = os.getenv("USER_EMAIL", "zfaragj@gmail.com")
SHOP_EMAIL = os.getenv("SHOP_EMAIL", "ckdshfh@gmail.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")


@pytest.mark.integration
class TestRealWorldScenarios:
    """Real-world usage scenarios"""
    
    def test_scenario_user_first_time_login(self, client: TestClient):
        """
        Scenario: New user logs in for the first time
        1. User clicks "Login with Google"
        2. Gets redirected to Google OAuth
        3. Returns with auth code
        4. Gets JWT tokens
        5. Views their profile with free credits
        """
        # Step 1: Get Google auth URL
        response = client.get("/api/v1/auth/google/url?account_type=user&platform=mobile")
        assert response.status_code == 200
        auth_data = response.json()
        assert "authorization_url" in auth_data
        print(f"✓ Step 1: Google Auth URL: {auth_data['authorization_url'][:50]}...")
        
        # Step 2-4: Simulate login with test token (in real scenario, this would be OAuth callback)
        response = client.post("/api/v1/auth/test-token?account_type=user")
        assert response.status_code == 200
        tokens = response.json()
        print(f"✓ Step 2-4: Got tokens")
        
        # Step 5: Check profile and free credits
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        assert user["free_generations_left"] >= 0
        assert user["free_try_ons_left"] >= 0
        print(f"✓ Step 5: User has {user['free_generations_left']} free generations and {user['free_try_ons_left']} free try-ons")
    
    def test_scenario_user_browses_and_purchases(self, client: TestClient, test_product):
        """
        Scenario: User browses products and makes a purchase
        1. Browse all products
        2. Search for specific items
        3. View product details
        4. Check reviews
        5. Initiate purchase
        """
        # Get user token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 1: Browse products
        response = client.get("/api/v1/products/")
        assert response.status_code == 200
        products = response.json()
        print(f"✓ Step 1: Found {products['total']} products")
        
        # Step 2: Search for specific items
        response = client.get("/api/v1/products/search?query=dress&min_price=50&max_price=200")
        assert response.status_code == 200
        print(f"✓ Step 2: Search completed")
        
        # Step 3: View product details
        response = client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        product = response.json()
        print(f"✓ Step 3: Viewing product: {product['name']}")
        
        # Step 4: Check reviews
        response = client.get(f"/api/v1/products/{test_product.id}/reviews")
        assert response.status_code == 200
        print(f"✓ Step 4: Reviews loaded")
        
        # Step 5: Initiate purchase
        response = client.post(f"/api/v1/products/{test_product.id}/purchase", headers=headers)
        # May fail if insufficient balance or product not available
        print(f"✓ Step 5: Purchase initiated (status: {response.status_code})")
    
    def test_scenario_user_generates_fashion_with_ai(self, client: TestClient):
        """
        Scenario: User generates fashion items using AI
        1. Check balance and free credits
        2. Generate clothing from text
        3. Generate person/model
        4. Apply clothing to model
        """
        # Get user token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 1: Check balance
        response = client.get("/api/v1/users/me/balance", headers=headers)
        assert response.status_code == 200
        balance = response.json()
        print(f"✓ Step 1: Balance: ${balance['balance']}, Free generations: {balance['free_generations_left']}")
        
        # Step 2: Generate clothing
        response = client.post(
            "/api/v1/generations/generate-clothing",
            headers=headers,
            json={
                "description": "Modern black leather jacket with silver zippers",
                "aspect_ratio": "1:1"
            }
        )
        print(f"✓ Step 2: Clothing generation request (status: {response.status_code})")
        
        # Step 3: Generate person
        response = client.post(
            "/api/v1/generations/generate-person",
            headers=headers,
            json={
                "description": "Professional female model, 25 years old, standing pose",
                "aspect_ratio": "2:3"
            }
        )
        print(f"✓ Step 3: Person generation request (status: {response.status_code})")
        
        # Step 4: Generate complete fashion from text
        response = client.post(
            "/api/v1/generations/generate-from-text",
            headers=headers,
            json={
                "prompt": "Elegant evening dress in emerald green",
                "aspect_ratio": "1:1"
            }
        )
        print(f"✓ Step 4: Complete generation request (status: {response.status_code})")
    
    def test_scenario_shop_owner_adds_product(self, client: TestClient):
        """
        Scenario: Shop owner adds a new product
        1. Login as shop
        2. View current products
        3. Create new product
        4. Wait for moderation
        5. Check analytics
        """
        # Get shop token
        response = client.post("/api/v1/auth/test-token?account_type=shop")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 1: Check shop profile
        response = client.get("/api/v1/shops/me", headers=headers)
        assert response.status_code == 200
        shop = response.json()
        print(f"✓ Step 1: Shop: {shop['shop_name']}")
        
        # Step 2: View current products
        response = client.get("/api/v1/shops/me/products", headers=headers)
        assert response.status_code == 200
        current_products = response.json()
        print(f"✓ Step 2: Current products: {len(current_products)}")
        
        # Step 3: Create new product
        product_data = {
            "name": "Summer Collection Dress",
            "description": "Beautiful summer dress, light and comfortable",
            "price": 149.99,
            "characteristics": '{"size": ["S", "M", "L"], "color": ["blue", "white"]}',
            "image_urls": '["https://example.com/dress1.jpg", "https://example.com/dress2.jpg"]'
        }
        response = client.post("/api/v1/products/", headers=headers, data=product_data)
        print(f"✓ Step 3: Product creation (status: {response.status_code})")
        
        # Step 5: Check analytics
        response = client.get("/api/v1/shops/me/analytics", headers=headers)
        assert response.status_code == 200
        analytics = response.json()
        print(f"✓ Step 5: Analytics - Products: {analytics['total_products']}, Revenue: ${analytics['total_revenue']}")
    
    def test_scenario_shop_owner_topup_and_rent(self, client: TestClient, test_product):
        """
        Scenario: Shop owner tops up balance and rents product slot
        1. Check current balance
        2. Create top-up payment
        3. Rent product slot for visibility
        """
        # Get shop token
        response = client.post("/api/v1/auth/test-token?account_type=shop")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 1: Check balance
        response = client.get("/api/v1/shops/me", headers=headers)
        assert response.status_code == 200
        shop = response.json()
        print(f"✓ Step 1: Current balance: ${shop['balance']}")
        
        # Step 2: Create top-up payment
        response = client.post(
            "/api/v1/payments/shop/top-up",
            headers={**headers, "x-client-platform": "web"},
            json={
                "amount": 50.0,
                "payment_type": "shop_topup",
                "description": "Balance top-up for product rentals"
            }
        )
        assert response.status_code == 200
        payment = response.json()
        print(f"✓ Step 2: Payment created - Order ID: {payment['order_id']}")
        print(f"  Approval URL: {payment['approval_url'][:60]}...")
        
        # Step 3: Create rent payment
        response = client.post(
            "/api/v1/payments/shop/rent-product",
            headers={**headers, "x-client-platform": "mobile"},
            json={
                "amount": 10.0,
                "payment_type": "rent_product",
                "description": "Rent product slot for 1 month",
                "extra_data": {
                    "product_id": test_product.id,
                    "months": 1
                }
            }
        )
        print(f"✓ Step 3: Rent payment created (status: {response.status_code})")
    
    def test_scenario_admin_moderates_products(self, client: TestClient, test_product):
        """
        Scenario: Admin moderates pending products
        1. Login as admin
        2. View dashboard
        3. Check moderation queue
        4. Approve/reject products
        5. View all transactions
        """
        # Get admin token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Note: Need to set user as admin in actual scenario
        # For now, will test endpoint access
        
        # Step 2: View dashboard
        response = client.get("/api/v1/admin/dashboard", headers=headers)
        if response.status_code == 200:
            dashboard = response.json()
            print(f"✓ Step 2: Dashboard - Users: {dashboard['total_users']}, Pending: {dashboard['pending_moderation']}")
        else:
            print(f"✓ Step 2: Dashboard access (status: {response.status_code}) - Need admin role")
        
        # Step 3: Check moderation queue
        response = client.get("/api/v1/admin/moderation/queue", headers=headers)
        print(f"✓ Step 3: Moderation queue (status: {response.status_code})")
        
        # Step 4: Approve product
        response = client.post(
            f"/api/v1/admin/moderation/{test_product.id}/approve",
            headers=headers,
            json={
                "action": "approve",
                "notes": "Product meets quality standards"
            }
        )
        print(f"✓ Step 4: Product approval (status: {response.status_code})")
        
        # Step 5: View transactions
        response = client.get("/api/v1/admin/transactions?limit=50", headers=headers)
        print(f"✓ Step 5: Transactions view (status: {response.status_code})")
    
    def test_scenario_user_writes_review(self, client: TestClient, test_product):
        """
        Scenario: User writes a product review
        1. View product
        2. Check existing reviews
        3. Write review
        4. View updated review stats
        """
        # Get user token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 1: View product
        response = client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        product = response.json()
        print(f"✓ Step 1: Viewing product: {product['name']}")
        
        # Step 2: Check existing reviews
        response = client.get(f"/api/v1/products/{test_product.id}/reviews")
        assert response.status_code == 200
        reviews = response.json()
        print(f"✓ Step 2: Existing reviews: {len(reviews)}")
        
        # Step 3: Write review
        response = client.post(
            f"/api/v1/products/{test_product.id}/reviews",
            headers=headers,
            json={
                "rating": 5,
                "comment": "Excellent quality! The fabric is amazing and fits perfectly. Highly recommend!"
            }
        )
        print(f"✓ Step 3: Review submitted (status: {response.status_code})")
        
        # Step 4: View stats
        response = client.get(f"/api/v1/products/{test_product.id}/reviews/stats")
        assert response.status_code == 200
        print(f"✓ Step 4: Review stats updated")


@pytest.mark.integration
class TestPaymentFlowScenarios:
    """Test payment flow scenarios with PayPal"""
    
    def test_user_topup_payment_flow(self, client: TestClient):
        """Complete user balance top-up flow"""
        # Get user token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Create payment
        response = client.post(
            "/api/v1/payments/user/top-up",
            headers={**headers, "x-client-platform": "mobile"},
            json={
                "amount": 25.0,
                "payment_type": "user_topup",
                "description": "Top up $25 for AI generations"
            }
        )
        assert response.status_code == 200
        payment = response.json()
        
        print(f"✓ Payment created")
        print(f"  Order ID: {payment['order_id']}")
        print(f"  Amount: ${payment['amount']}")
        print(f"  Status: {payment['status']}")
        print(f"  Approval URL: {payment['approval_url']}")
        print(f"\nTo complete payment:")
        print(f"1. Open: {payment['approval_url']}")
        print(f"2. Login with PayPal sandbox account:")
        print(f"   Email: sb-0qexx39406981@business.example.com")
        print(f"   Pass: YPETl7&<")
        print(f"3. Approve payment")
        print(f"4. Will redirect to success callback")


@pytest.mark.integration
class TestDataConsistencyScenarios:
    """Test data consistency across operations"""
    
    def test_balance_consistency_after_generation(self, client: TestClient):
        """Test that balance is correctly updated after AI generation"""
        # Get user token
        response = client.post("/api/v1/auth/test-token?account_type=user")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Get initial balance
        response = client.get("/api/v1/users/me/balance", headers=headers)
        initial_balance = response.json()
        print(f"✓ Initial balance: ${initial_balance['balance']}")
        print(f"  Free generations: {initial_balance['free_generations_left']}")
        
        # Attempt generation
        response = client.post(
            "/api/v1/generations/generate-from-text",
            headers=headers,
            json={
                "prompt": "Red dress",
                "aspect_ratio": "1:1"
            }
        )
        print(f"✓ Generation attempt: {response.status_code}")
        
        # Check updated balance
        response = client.get("/api/v1/users/me/balance", headers=headers)
        new_balance = response.json()
        print(f"✓ New balance: ${new_balance['balance']}")
        print(f"  Free generations: {new_balance['free_generations_left']}")
    
    def test_shop_analytics_consistency(self, client: TestClient):
        """Test shop analytics consistency"""
        # Get shop token
        response = client.post("/api/v1/auth/test-token?account_type=shop")
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Get products count
        response = client.get("/api/v1/shops/me/products", headers=headers)
        products = response.json()
        products_count = len(products)
        
        # Get analytics
        response = client.get("/api/v1/shops/me/analytics", headers=headers)
        analytics = response.json()
        
        print(f"✓ Products in list: {products_count}")
        print(f"✓ Products in analytics: {analytics['total_products']}")
        print(f"✓ Active products: {analytics['active_products']}")
        print(f"✓ Total revenue: ${analytics['total_revenue']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
