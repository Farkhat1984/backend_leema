"""
Tests for generation endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.product import Product
from unittest.mock import AsyncMock, patch


@pytest.mark.generation
class TestGenerationEndpoints:
    """Test generation endpoints"""

    @pytest.mark.anyio
    async def test_generate_fashion(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test generating fashion with AI"""
        with patch('app.services.user_service.user_service.charge_for_generation') as mock_charge, \
             patch('app.services.generation_service.generation_service.generate_fashion') as mock_gen:
            from app.models.generation import Generation, GenerationType
            from datetime import datetime, timezone

            # Mock charge response
            mock_charge.return_value = {
                "charged_from": "free",
                "amount": 0,
                "remaining_free": 4
            }

            # Mock generation response
            mock_generation = Generation(
                id=1,
                user_id=test_user.id,
                type=GenerationType.GENERATION,
                created_at=datetime.now(timezone.utc),
                image_url="https://example.com/generated.jpg",
                cost=1.0
            )
            mock_gen.return_value = mock_generation

            request_data = {
                "prompt": "Red dress",
                "user_image_url": "https://example.com/user.jpg"
            }
            response = await client.post(
                "/api/v1/generations/generate",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "generation"
            # Prompt not in response
            assert "image_url" in data

    @pytest.mark.anyio
    async def test_generate_fashion_no_balance(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test generating fashion with insufficient balance"""
        with patch('app.services.user_service.user_service.charge_for_generation') as mock_charge:
            # Mock insufficient balance error
            mock_charge.side_effect = ValueError("Insufficient balance")

            request_data = {
                "prompt": "Blue shirt"
            }
            response = await client.post(
                "/api/v1/generations/generate",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 402

    @pytest.mark.anyio
    async def test_generate_fashion_unauthorized(self, client: AsyncClient):
        """Test generating fashion without auth"""
        request_data = {
            "prompt": "Green pants"
        }
        response = await client.post(
            "/api/v1/generations/generate",
            json=request_data
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_try_on_product(
        self,
        client: AsyncClient,
        test_user: User,
        test_product: Product,
        auth_headers_user: dict
    ):
        """Test trying on a product"""
        with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge, \
             patch('app.services.generation_service.generation_service.try_on_product') as mock_tryon:
            from app.models.generation import Generation, GenerationType
            from datetime import datetime, timezone

            # Mock charge response
            mock_charge.return_value = {
                "charged_from": "free",
                "amount": 0,
                "remaining_free": 4
            }

            # Mock try-on response
            mock_generation = Generation(
                id=2,
                user_id=test_user.id,
                type=GenerationType.TRY_ON,
                product_id=test_product.id,
                created_at=datetime.now(timezone.utc),
                image_url="https://example.com/tryon.jpg",
                cost=0.5
            )
            mock_tryon.return_value = mock_generation

            request_data = {
                "product_id": test_product.id,
                "user_image_url": "https://example.com/user.jpg"
            }
            response = await client.post(
                "/api/v1/generations/try-on",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "try_on"
            assert data["product_id"] == test_product.id
            assert "image_url" in data

    @pytest.mark.anyio
    async def test_try_on_product_no_balance(
        self,
        client: AsyncClient,
        test_user: User,
        test_product: Product,
        auth_headers_user: dict
    ):
        """Test trying on product with insufficient balance"""
        with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge:
            # Mock insufficient balance error
            mock_charge.side_effect = ValueError("Insufficient balance")

            request_data = {
                "product_id": test_product.id,
                "user_image_url": "https://example.com/user.jpg"
            }
            response = await client.post(
                "/api/v1/generations/try-on",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 402

    @pytest.mark.anyio
    async def test_try_on_product_unauthorized(
        self,
        client: AsyncClient,
        test_product: Product
    ):
        """Test trying on product without auth"""
        request_data = {
            "product_id": test_product.id,
            "user_image_url": "https://example.com/user.jpg"
        }
        response = await client.post(
            "/api/v1/generations/try-on",
            json=request_data
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_try_on_invalid_product(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test trying on non-existent product"""
        with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge, \
             patch('app.services.generation_service.generation_service.try_on_product') as mock_tryon:
            # Mock charge success but generation failure
            mock_charge.return_value = {
                "charged_from": "free",
                "amount": 0,
                "remaining_free": 4
            }
            mock_tryon.return_value = None

            request_data = {
                "product_id": 99999,
                "user_image_url": "https://example.com/user.jpg"
            }
            response = await client.post(
                "/api/v1/generations/try-on",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 400

    @pytest.mark.anyio
    async def test_generate_missing_prompt(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test generating without prompt"""
        request_data = {}
        response = await client.post(
            "/api/v1/generations/generate",
            headers=auth_headers_user,
            json=request_data
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.anyio
    async def test_apply_clothing_to_model(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test applying clothing from image to model"""
        with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge, \
             patch('app.services.generation_service.generation_service.apply_clothing_to_model') as mock_apply:
            from app.models.generation import Generation, GenerationType
            from datetime import datetime, timezone

            # Mock charge response
            mock_charge.return_value = {
                "charged_from": "free",
                "amount": 0,
                "remaining_free": 4
            }

            # Mock apply clothing response
            mock_generation = Generation(
                id=3,
                user_id=test_user.id,
                type=GenerationType.TRY_ON,
                created_at=datetime.now(timezone.utc),
                image_url="https://example.com/applied.jpg",
                cost=0.5
            )
            mock_apply.return_value = mock_generation

            request_data = {
                "clothing_image_url": "https://example.com/clothing.jpg",
                "person_image_url": "https://example.com/person.jpg"
            }
            response = await client.post(
                "/api/v1/generations/apply-clothing",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "try_on"
            assert "image_url" in data
            assert data["charge_info"]["charged_from"] == "free"

    @pytest.mark.anyio
    async def test_apply_clothing_no_balance(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test applying clothing with insufficient balance"""
        with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge:
            # Mock insufficient balance error
            mock_charge.side_effect = ValueError("Insufficient balance")

            request_data = {
                "clothing_image_url": "https://example.com/clothing.jpg",
                "person_image_url": "https://example.com/person.jpg"
            }
            response = await client.post(
                "/api/v1/generations/apply-clothing",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 402

    @pytest.mark.anyio
    async def test_apply_clothing_unauthorized(self, client: AsyncClient):
        """Test applying clothing without auth"""
        request_data = {
            "clothing_image_url": "https://example.com/clothing.jpg",
            "person_image_url": "https://example.com/person.jpg"
        }
        response = await client.post(
            "/api/v1/generations/apply-clothing",
            json=request_data
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_apply_clothing_missing_params(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test applying clothing with missing parameters"""
        # Missing person_image_url
        request_data = {
            "clothing_image_url": "https://example.com/clothing.jpg"
        }
        response = await client.post(
            "/api/v1/generations/apply-clothing",
            headers=auth_headers_user,
            json=request_data
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.anyio
    async def test_apply_clothing_generation_failed(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers_user: dict
    ):
        """Test applying clothing when AI generation fails"""
        with patch('app.services.user_service.user_service.charge_for_tryon') as mock_charge, \
             patch('app.services.generation_service.generation_service.apply_clothing_to_model') as mock_apply:
            # Mock charge success but generation failure
            mock_charge.return_value = {
                "charged_from": "free",
                "amount": 0,
                "remaining_free": 4
            }
            mock_apply.return_value = None

            request_data = {
                "clothing_image_url": "https://example.com/clothing.jpg",
                "person_image_url": "https://example.com/person.jpg"
            }
            response = await client.post(
                "/api/v1/generations/apply-clothing",
                headers=auth_headers_user,
                json=request_data
            )
            assert response.status_code == 400
