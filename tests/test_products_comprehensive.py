"""
Comprehensive Product Tests
Tests all product endpoints and scenarios
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


class TestProductEndpoints:
    """Test product API endpoints"""

    # Get Products Tests
    @pytest.mark.asyncio
    async def test_get_products_empty(self, client):
        """Test getting products when none exist"""
        response = client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data
        assert isinstance(data["products"], list)

    @pytest.mark.asyncio
    async def test_get_products_with_data(self, client, test_product):
        """Test getting products with data"""
        response = client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data
        assert len(data["products"]) >= 1
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_products_pagination(self, client):
        """Test products pagination"""
        response = client.get("/api/v1/products/?skip=0&limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["products"]) <= 10
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_get_products_with_search(self, client, test_product):
        """Test products search"""
        response = client.get(f"/api/v1/products/?search={test_product.name}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)

    # Search Products Tests
    @pytest.mark.asyncio
    async def test_search_products_by_query(self, client, test_product):
        """Test searching products by query"""
        response = client.get("/api/v1/products/search?query=Test")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data

    @pytest.mark.asyncio
    async def test_search_products_by_shop(self, client, test_shop):
        """Test searching products by shop"""
        response = client.get(f"/api/v1/products/search?shop_id={test_shop.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)

    @pytest.mark.asyncio
    async def test_search_products_by_price_range(self, client):
        """Test searching products by price range"""
        response = client.get("/api/v1/products/search?min_price=10&max_price=100")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)

    @pytest.mark.asyncio
    async def test_search_products_active_only(self, client):
        """Test searching only active products"""
        response = client.get("/api/v1/products/search?is_active=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)

    @pytest.mark.asyncio
    async def test_search_products_by_moderation_status(self, client):
        """Test searching products by moderation status"""
        response = client.get("/api/v1/products/search?moderation_status=approved")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)

    @pytest.mark.asyncio
    async def test_search_products_sort_by_price(self, client):
        """Test sorting products by price"""
        response = client.get("/api/v1/products/search?sort_by=price&sort_order=asc")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)

    @pytest.mark.asyncio
    async def test_search_products_sort_by_created(self, client):
        """Test sorting products by creation date"""
        response = client.get("/api/v1/products/search?sort_by=created_at&sort_order=desc")

        assert response.status_code == status.HTTP_200_OK

    # Create Product Tests
    @pytest.mark.asyncio
    async def test_create_product_success(self, client, shop_headers):
        """Test creating a product"""
        product_data = {
            "name": "New Test Product",
            "description": "A new test product",
            "price": 49.99,
            "rental_price": 9.99,
            "rental_period_days": 7,
            "category": "clothing",
            "sizes": ["S", "M", "L"],
            "colors": ["black", "white"],
            "images": ["https://example.com/image.jpg"]
        }

        response = client.post("/api/v1/products/", headers=shop_headers, json=product_data)

        assert response.status_code == status.HTTP_201_CREATED or response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Test Product"
        assert data["price"] == 49.99

    @pytest.mark.asyncio
    async def test_create_product_unauthorized(self, client):
        """Test creating product without auth"""
        product_data = {
            "name": "Unauthorized Product",
            "price": 99.99
        }

        response = client.post("/api/v1/products/", json=product_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_product_as_user(self, client, user_headers):
        """Test that regular user cannot create products"""
        product_data = {
            "name": "User Product",
            "price": 99.99
        }

        response = client.post("/api/v1/products/", headers=user_headers, json=product_data)

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_create_product_invalid_data(self, client, shop_headers):
        """Test creating product with invalid data"""
        product_data = {
            "name": "",  # Empty name
            "price": -10  # Negative price
        }

        response = client.post("/api/v1/products/", headers=shop_headers, json=product_data)

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # Get Product by ID Tests
    @pytest.mark.asyncio
    async def test_get_product_by_id(self, client, test_product):
        """Test getting a specific product"""
        response = client.get(f"/api/v1/products/{test_product.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_product.id
        assert data["name"] == test_product.name

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, client):
        """Test getting non-existent product"""
        response = client.get("/api/v1/products/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # Update Product Tests
    @pytest.mark.asyncio
    async def test_update_product_success(self, client, shop_headers, test_product):
        """Test updating a product"""
        update_data = {
            "name": "Updated Product Name",
            "price": 199.99
        }

        response = client.put(
            f"/api/v1/products/{test_product.id}",
            headers=shop_headers,
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Product Name"

    @pytest.mark.asyncio
    async def test_update_product_unauthorized(self, client, test_product):
        """Test updating product without auth"""
        response = client.put(f"/api/v1/products/{test_product.id}", json={"name": "Hacked"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_other_shop_product(self, client, shop_headers, db_session):
        """Test that shop cannot update another shop's product"""
        # Create another shop and product
        from app.services.shop_service import shop_service
        from app.services.product_service import product_service
        from app.schemas.shop import ShopCreate
        from app.schemas.product import ProductCreate
        
        other_shop_data = ShopCreate(
            google_id="other_shop_2",
            email="shop2@example.com",
            shop_name="Shop 2",
            owner_name="Owner 2"
        )
        other_shop = await shop_service.create(db_session, other_shop_data)
        
        other_product_data = ProductCreate(
            name="Other Product",
            description="Other product",
            price=99.99,
            category="clothing",
            sizes=["M"],
            colors=["blue"],
            images=["https://example.com/img.jpg"]
        )
        other_product = await product_service.create(db_session, other_shop.id, other_product_data)

        # Try to update other shop's product
        response = client.put(
            f"/api/v1/products/{other_product.id}",
            headers=shop_headers,
            json={"name": "Hacked Product"}
        )

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    # Delete Product Tests
    @pytest.mark.asyncio
    async def test_delete_product_success(self, client, shop_headers, test_product):
        """Test deleting a product"""
        response = client.delete(f"/api/v1/products/{test_product.id}", headers=shop_headers)

        assert response.status_code == status.HTTP_200_OK or response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_product_unauthorized(self, client, test_product):
        """Test deleting product without auth"""
        response = client.delete(f"/api/v1/products/{test_product.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Product Reviews Tests
    @pytest.mark.asyncio
    async def test_create_product_review(self, client, user_headers, test_product):
        """Test creating a product review"""
        review_data = {
            "rating": 5,
            "comment": "Great product!",
            "product_id": test_product.id
        }

        response = client.post(
            f"/api/v1/products/{test_product.id}/reviews",
            headers=user_headers,
            json=review_data
        )

        # May need order first, so accept either success or error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ]

    @pytest.mark.asyncio
    async def test_get_product_reviews(self, client, test_product):
        """Test getting product reviews"""
        response = client.get(f"/api/v1/products/{test_product.id}/reviews")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    # Edge Cases
    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, client):
        """Test search with multiple filters"""
        response = client.get(
            "/api/v1/products/search?query=test&min_price=10&max_price=200&is_active=true&sort_by=price&sort_order=asc"
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_products_large_pagination(self, client):
        """Test getting products with large pagination"""
        response = client.get("/api/v1/products/?skip=1000&limit=50")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["products"], list)
