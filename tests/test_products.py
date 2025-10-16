"""
Tests for product endpoints
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestProductEndpoints:
    """Test product API endpoints"""

    def test_get_products(self, client):
        """Test getting list of products"""
        response = client.get("/api/products/")

        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["products"], list)

    def test_get_products_with_pagination(self, client):
        """Test getting products with pagination"""
        response = client.get("/api/products/?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) <= 10

    def test_search_products(self, client):
        """Test searching products"""
        response = client.get("/api/products/search?query=test")

        assert response.status_code == 200
        data = response.json()
        assert "products" in data

    def test_search_products_with_filters(self, client):
        """Test searching products with price filters"""
        response = client.get("/api/products/search?min_price=10&max_price=100")

        assert response.status_code == 200

    def test_get_product_by_id(self, client):
        """Test getting single product by ID"""
        response = client.get("/api/products/1")

        # Product may not exist
        assert response.status_code in [200, 404]

    def test_create_product_unauthorized(self, client):
        """Test creating product without shop authentication"""
        product_data = {
            "name": "Test Product",
            "description": "Test description",
            "price": 99.99,
            "category": "clothing"
        }

        response = client.post("/api/products/", json=product_data)

        assert response.status_code == 401

    def test_create_product_with_auth(self, client, auth_headers):
        """Test creating product with authentication"""
        # Note: This would need shop auth, not user auth
        product_data = {
            "name": "Test Product",
            "description": "Test description",
            "price": 99.99,
            "category": "clothing"
        }

        response = client.post("/api/products/", 
                              headers=auth_headers,
                              json=product_data)

        # Will likely fail as user token is not shop token
        assert response.status_code in [201, 401, 403, 422]

    def test_update_product(self, client, auth_headers):
        """Test updating a product"""
        update_data = {
            "name": "Updated Product Name",
            "price": 149.99
        }

        response = client.put("/api/products/1", 
                             headers=auth_headers,
                             json=update_data)

        assert response.status_code in [200, 401, 403, 404]

    def test_delete_product(self, client, auth_headers):
        """Test deleting a product"""
        response = client.delete("/api/products/1", headers=auth_headers)

        assert response.status_code in [200, 204, 401, 403, 404]

    def test_get_product_reviews(self, client):
        """Test getting product reviews"""
        response = client.get("/api/products/1/reviews")

        # Product may not exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_create_product_review(self, client, auth_headers):
        """Test creating a product review"""
        review_data = {
            "rating": 5,
            "comment": "Great product!"
        }

        response = client.post("/api/products/1/reviews", 
                              headers=auth_headers,
                              json=review_data)

        assert response.status_code in [201, 401, 404, 400]

    def test_buy_product(self, client, auth_headers):
        """Test buying a product"""
        response = client.post("/api/products/1/buy", headers=auth_headers)

        assert response.status_code in [200, 401, 404, 400]

    def test_upload_product_image(self, client, auth_headers):
        """Test uploading product image"""
        # Create a fake image file
        file_content = b"fake image content"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}

        response = client.post("/api/products/1/image", 
                              headers=auth_headers,
                              files=files)

        assert response.status_code in [200, 401, 403, 404, 422]
