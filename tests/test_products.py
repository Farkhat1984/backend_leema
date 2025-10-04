"""
Tests for product endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.shop import Shop
from app.models.product import Product


@pytest.mark.product
class TestProductEndpoints:
    """Test product endpoints"""

    @pytest.mark.anyio
    async def test_get_products(self, client: AsyncClient, test_product: Product):
        """Test getting active products"""
        response = await client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["products"], list)

    @pytest.mark.anyio
    async def test_get_products_pagination(self, client: AsyncClient):
        """Test getting products with pagination"""
        response = await client.get("/api/v1/products/?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) <= 10

    @pytest.mark.anyio
    async def test_get_products_search(self, client: AsyncClient, test_product: Product):
        """Test searching products"""
        response = await client.get("/api/v1/products/?search=Test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["products"], list)

    @pytest.mark.anyio
    async def test_get_product_by_id(self, client: AsyncClient, test_product: Product):
        """Test getting product by ID"""
        response = await client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id
        assert data["name"] == test_product.name
        assert float(data["price"]) == float(test_product.price)

    @pytest.mark.anyio
    async def test_get_product_not_found(self, client: AsyncClient):
        """Test getting non-existent product"""
        response = await client.get("/api/v1/products/99999")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_create_product(
        self,
        client: AsyncClient,
        test_shop: Shop,
        auth_headers_shop: dict
    ):
        """Test creating a product"""
        product_data = {
            "name": "New Product",
            "description": "Product description",
            "price": "149.99",
            "image_urls": "https://example.com/image1.jpg,https://example.com/image2.jpg"
        }
        response = await client.post(
            "/api/v1/products/",
            headers=auth_headers_shop,
            data=product_data  # Use form data instead of json
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Product"
        assert float(data["price"]) == 149.99
        assert data["moderation_status"] == "pending"

    @pytest.mark.anyio
    async def test_create_product_unauthorized(self, client: AsyncClient):
        """Test creating product without auth"""
        product_data = {
            "name": "New Product",
            "price": 99.99
        }
        response = await client.post(
            "/api/v1/products/",
            json=product_data
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_create_product_invalid_data(
        self,
        client: AsyncClient,
        auth_headers_shop: dict
    ):
        """Test creating product with invalid data"""
        product_data = {
            "name": "",  # Empty name
            "price": -10  # Negative price
        }
        response = await client.post(
            "/api/v1/products/",
            headers=auth_headers_shop,
            json=product_data
        )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_update_product(
        self,
        client: AsyncClient,
        test_shop: Shop,
        test_product: Product,
        auth_headers_shop: dict,
        db_session: AsyncSession
    ):
        """Test updating a product"""
        # Make sure test_product belongs to test_shop
        test_product.shop_id = test_shop.id
        await db_session.commit()

        update_data = {
            "name": "Updated Product Name",
            "price": 199.99
        }
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers_shop,
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Product Name"
        assert data["price"] == 199.99

    @pytest.mark.anyio
    async def test_update_product_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_product: Product,
        auth_headers_shop: dict
    ):
        """Test updating product not owned by shop"""
        # Create another shop that doesn't own the product
        from app.schemas.shop import ShopCreate
        from app.services.shop_service import shop_service
        from app.core.security import create_access_token

        another_shop_data = ShopCreate(
            google_id="another_shop_456",
            email="anothershop@example.com",
            shop_name="Another Shop",
            owner_name="Another Owner"
        )
        another_shop = await shop_service.create(db_session, another_shop_data)
        await db_session.commit()

        # Create token for another shop
        another_shop_token = create_access_token({"shop_id": another_shop.id})
        another_shop_headers = {"Authorization": f"Bearer {another_shop_token}"}

        update_data = {
            "name": "Hacked Product"
        }
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=another_shop_headers,
            json=update_data
        )
        # Should fail if product doesn't belong to shop
        assert response.status_code in [404, 403]

    @pytest.mark.anyio
    async def test_delete_product(
        self,
        client: AsyncClient,
        test_shop: Shop,
        test_product: Product,
        auth_headers_shop: dict,
        db_session: AsyncSession
    ):
        """Test deleting a product"""
        # Make sure test_product belongs to test_shop
        test_product.shop_id = test_shop.id
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers_shop
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_delete_product_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_product: Product,
        auth_headers_shop: dict
    ):
        """Test deleting product not owned by shop"""
        # Create another shop that doesn't own the product
        from app.schemas.shop import ShopCreate
        from app.services.shop_service import shop_service
        from app.core.security import create_access_token

        another_shop_data = ShopCreate(
            google_id="another_shop_789",
            email="yetanothershop@example.com",
            shop_name="Yet Another Shop",
            owner_name="Yet Another Owner"
        )
        another_shop = await shop_service.create(db_session, another_shop_data)
        await db_session.commit()

        # Create token for another shop
        another_shop_token = create_access_token({"shop_id": another_shop.id})
        another_shop_headers = {"Authorization": f"Bearer {another_shop_token}"}

        response = await client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=another_shop_headers
        )
        # Should fail if product doesn't belong to shop
        assert response.status_code in [404, 403]

    @pytest.mark.anyio
    async def test_user_cannot_create_product(
        self,
        client: AsyncClient,
        auth_headers_user: dict
    ):
        """Test that user cannot create products"""
        product_data = {
            "name": "User Product",
            "price": 99.99
        }
        response = await client.post(
            "/api/v1/products/",
            headers=auth_headers_user,
            json=product_data
        )
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_upload_product_images(
        self,
        client: AsyncClient,
        auth_headers_shop: dict
    ):
        """Test uploading product images"""
        from io import BytesIO

        # Create fake image file
        fake_image = BytesIO(b"fake image data")
        fake_image.name = "test.jpg"

        files = {
            "files": ("test.jpg", fake_image, "image/jpeg")
        }

        response = await client.post(
            "/api/v1/products/upload-images",
            headers=auth_headers_shop,
            files=files
        )
        assert response.status_code == 200
        data = response.json()
        assert "urls" in data
        assert isinstance(data["urls"], list)

    @pytest.mark.anyio
    async def test_upload_product_images_invalid_type(
        self,
        client: AsyncClient,
        auth_headers_shop: dict
    ):
        """Test uploading invalid file type"""
        from io import BytesIO

        # Create fake text file
        fake_file = BytesIO(b"not an image")
        fake_file.name = "test.txt"

        files = {
            "files": ("test.txt", fake_file, "text/plain")
        }

        response = await client.post(
            "/api/v1/products/upload-images",
            headers=auth_headers_shop,
            files=files
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_upload_product_images_unauthorized(
        self,
        client: AsyncClient
    ):
        """Test uploading images without auth"""
        from io import BytesIO

        fake_image = BytesIO(b"fake image data")
        fake_image.name = "test.jpg"

        files = {
            "files": ("test.jpg", fake_image, "image/jpeg")
        }

        response = await client.post(
            "/api/v1/products/upload-images",
            files=files
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_purchase_product(
        self,
        client: AsyncClient,
        test_product: Product,
        auth_headers_user: dict
    ):
        """Test purchasing a product"""
        from unittest.mock import patch

        with patch('app.services.payment_service.payment_service.process_product_purchase') as mock_payment:
            mock_payment.return_value = {
                "order_id": "test_order_123",
                "approval_url": "https://paypal.com/approve",
                "amount": 99.99
            }

            response = await client.post(
                f"/api/v1/products/{test_product.id}/purchase",
                headers=auth_headers_user
            )
            assert response.status_code == 200
            data = response.json()
            assert "order_id" in data
            assert "approval_url" in data
            assert data["status"] == "pending"

    @pytest.mark.anyio
    async def test_purchase_product_unauthorized(
        self,
        client: AsyncClient,
        test_product: Product
    ):
        """Test purchasing without auth"""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/purchase"
        )
        assert response.status_code == 403  # No Authorization header

    @pytest.mark.anyio
    async def test_purchase_nonexistent_product(
        self,
        client: AsyncClient,
        auth_headers_user: dict
    ):
        """Test purchasing non-existent product"""
        from unittest.mock import patch

        with patch('app.services.payment_service.payment_service.process_product_purchase') as mock_payment:
            mock_payment.return_value = None

            response = await client.post(
                "/api/v1/products/99999/purchase",
                headers=auth_headers_user
            )
            assert response.status_code == 400
