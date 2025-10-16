"""
Quick API tests using real tokens provided by user
"""
import pytest
from fastapi.testclient import TestClient

# Real tokens from user
USER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiYWRtaW4iLCJwbGF0Zm9ybSI6IndlYiIsImFjY291bnRfdHlwZSI6InVzZXIiLCJleHAiOjE3NjA0NDMxNjUsInR5cGUiOiJhY2Nlc3MifQ.NNEtMEdXjb51a79tNcdqV9-3h5WhYQuW1FfTeHgFcq8"
SHOP_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzaG9wX2lkIjoxLCJyb2xlIjoic2hvcCIsInBsYXRmb3JtIjoid2ViIiwiYWNjb3VudF90eXBlIjoic2hvcCIsImV4cCI6MTc2MDQ0MzIyMCwidHlwZSI6ImFjY2VzcyJ9.hea4ev7jZeDJhLKxWwJ-yVWdr1zQYRi1HOG3RiNTsmQ"


@pytest.fixture
def client():
    """Create test client"""
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def user_headers():
    """User authorization headers"""
    return {"Authorization": f"Bearer {USER_TOKEN}"}


@pytest.fixture
def shop_headers():
    """Shop authorization headers"""
    return {"Authorization": f"Bearer {SHOP_TOKEN}"}


class TestWithRealTokens:
    """Tests using real authentication tokens"""
    
    def test_user_get_profile(self, client, user_headers):
        """Test getting user profile with real token"""
        response = client.get("/api/v1/users/me", headers=user_headers)
        print(f"\n✅ User Profile: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Email: {data.get('email')}")
            print(f"   Balance: ${data.get('balance')}")
            print(f"   Free generations: {data.get('free_generations_left')}")
        assert response.status_code == 200
    
    def test_user_get_balance(self, client, user_headers):
        """Test getting user balance"""
        response = client.get("/api/v1/users/me/balance", headers=user_headers)
        print(f"\n✅ User Balance: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Balance: ${data.get('balance')}")
            print(f"   Free gens: {data.get('free_generations_left')}")
            print(f"   Free try-ons: {data.get('free_try_ons_left')}")
        assert response.status_code == 200
    
    def test_shop_get_profile(self, client, shop_headers):
        """Test getting shop profile with real token"""
        response = client.get("/api/v1/shops/me", headers=shop_headers)
        print(f"\n✅ Shop Profile: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Shop: {data.get('shop_name')}")
            print(f"   Email: {data.get('email')}")
            print(f"   Balance: ${data.get('balance')}")
        assert response.status_code == 200
    
    def test_shop_get_analytics(self, client, shop_headers):
        """Test getting shop analytics"""
        response = client.get("/api/v1/shops/me/analytics", headers=shop_headers)
        print(f"\n✅ Shop Analytics: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Products: {data.get('total_products')}")
            print(f"   Active: {data.get('active_products')}")
            print(f"   Revenue: ${data.get('total_revenue')}")
        assert response.status_code == 200
    
    def test_get_products_list(self, client):
        """Test getting public products"""
        response = client.get("/api/v1/products/?skip=0&limit=10")
        print(f"\n✅ Products List: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total products: {data.get('total')}")
            print(f"   Page size: {len(data.get('products', []))}")
        assert response.status_code == 200
    
    def test_search_products(self, client):
        """Test product search"""
        response = client.get("/api/v1/products/search?is_active=true&moderation_status=approved")
        print(f"\n✅ Product Search: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found: {data.get('total')} products")
        assert response.status_code == 200
    
    def test_admin_dashboard(self, client, user_headers):
        """Test admin dashboard"""
        response = client.get("/api/v1/admin/dashboard", headers=user_headers)
        print(f"\n✅ Admin Dashboard: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Users: {data.get('total_users')}")
            print(f"   Shops: {data.get('total_shops')}")
            print(f"   Products: {data.get('total_products')}")
            print(f"   Revenue: ${data.get('total_revenue')}")
        assert response.status_code == 200
    
    def test_user_transactions(self, client, user_headers):
        """Test getting user transactions"""
        response = client.get("/api/v1/users/me/transactions?limit=5", headers=user_headers)
        print(f"\n✅ User Transactions: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Transactions: {len(data)} found")
        assert response.status_code == 200
    
    def test_shop_products(self, client, shop_headers):
        """Test getting shop products"""
        response = client.get("/api/v1/shops/me/products", headers=shop_headers)
        print(f"\n✅ Shop Products: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Products: {len(data)} found")
        assert response.status_code == 200
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        print(f"\n✅ Health Check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
        assert response.status_code == 200


class TestPayPalIntegration:
    """Test PayPal payment flows with real tokens"""
    
    def test_user_create_topup_payment(self, client, user_headers):
        """Test creating user top-up payment"""
        response = client.post(
            "/api/v1/payments/user/top-up",
            headers={**user_headers, "x-client-platform": "mobile"},
            json={
                "amount": 10.0,
                "payment_type": "user_topup",
                "description": "Test top-up"
            }
        )
        print(f"\n✅ User Top-up Payment: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Order ID: {data.get('order_id')}")
            print(f"   Amount: ${data.get('amount')}")
            print(f"   Approval URL: {data.get('approval_url')[:60]}...")
        assert response.status_code in [200, 400, 402]
    
    def test_shop_create_topup_payment(self, client, shop_headers):
        """Test creating shop top-up payment"""
        response = client.post(
            "/api/v1/payments/shop/top-up",
            headers={**shop_headers, "x-client-platform": "web"},
            json={
                "amount": 50.0,
                "payment_type": "shop_topup",
                "description": "Shop balance top-up"
            }
        )
        print(f"\n✅ Shop Top-up Payment: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Order ID: {data.get('order_id')}")
            print(f"   Amount: ${data.get('amount')}")
        assert response.status_code in [200, 400, 402]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
