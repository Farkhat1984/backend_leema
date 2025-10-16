"""
Comprehensive Generation/AI Tests
Tests all AI generation endpoints including Gemini integration
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock


class TestGenerationEndpoints:
    """Test AI generation API endpoints"""

    # Fashion Generation Tests
    @pytest.mark.asyncio
    @patch('app.services.generation_service.generation_service.generate_fashion')
    @patch('app.services.user_service.user_service.charge_for_generation')
    async def test_generate_fashion_success(self, mock_charge, mock_generate, client, user_headers, test_user):
        """Test successful fashion generation"""
        mock_charge.return_value = {"amount": 5.0, "method": "balance"}
        mock_generate.return_value = MagicMock(
            id=1,
            user_id=test_user.id,
            prompt="summer dress",
            image_url="https://example.com/generated.jpg",
            cost=5.0
        )

        generation_data = {
            "prompt": "summer dress",
            "user_image_url": "https://example.com/user.jpg"
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=user_headers,
            json=generation_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_generate_fashion_unauthorized(self, client):
        """Test generation without auth"""
        generation_data = {
            "prompt": "summer dress"
        }

        response = client.post("/api/v1/generations/generate", json=generation_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch('app.services.user_service.user_service.charge_for_generation')
    async def test_generate_fashion_insufficient_balance(self, mock_charge, client, user_headers):
        """Test generation with insufficient balance"""
        mock_charge.side_effect = ValueError("Insufficient balance")

        generation_data = {
            "prompt": "expensive dress"
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=user_headers,
            json=generation_data
        )

        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    @pytest.mark.asyncio
    async def test_generate_fashion_empty_prompt(self, client, user_headers):
        """Test generation with empty prompt"""
        generation_data = {
            "prompt": ""
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=user_headers,
            json=generation_data
        )

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # Try-on Tests
    @pytest.mark.asyncio
    @patch('app.services.generation_service.generation_service.try_on_product')
    @patch('app.services.user_service.user_service.charge_for_tryon')
    async def test_tryon_product_success(self, mock_charge, mock_tryon, client, user_headers, test_product):
        """Test successful product try-on"""
        mock_charge.return_value = {"amount": 3.0, "method": "free_credit"}
        mock_tryon.return_value = MagicMock(
            id=1,
            user_id=1,
            product_id=test_product.id,
            image_url="https://example.com/tryon.jpg",
            cost=3.0
        )

        tryon_data = {
            "product_id": test_product.id,
            "user_image_url": "https://example.com/user.jpg"
        }

        response = client.post(
            "/api/v1/generations/try-on",
            headers=user_headers,
            json=tryon_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_tryon_unauthorized(self, client, test_product):
        """Test try-on without auth"""
        tryon_data = {
            "product_id": test_product.id,
            "user_image_url": "https://example.com/user.jpg"
        }

        response = client.post("/api/v1/generations/try-on", json=tryon_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch('app.services.user_service.user_service.charge_for_tryon')
    async def test_tryon_insufficient_credits(self, mock_charge, client, user_headers, test_product):
        """Test try-on with insufficient credits"""
        mock_charge.side_effect = ValueError("Insufficient credits")

        tryon_data = {
            "product_id": test_product.id,
            "user_image_url": "https://example.com/user.jpg"
        }

        response = client.post(
            "/api/v1/generations/try-on",
            headers=user_headers,
            json=tryon_data
        )

        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    @pytest.mark.asyncio
    async def test_tryon_invalid_product(self, client, user_headers):
        """Test try-on with non-existent product"""
        tryon_data = {
            "product_id": 99999,
            "user_image_url": "https://example.com/user.jpg"
        }

        response = client.post(
            "/api/v1/generations/try-on",
            headers=user_headers,
            json=tryon_data
        )

        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]

    # Apply Clothing Tests
    @pytest.mark.asyncio
    @patch('app.core.gemini.gemini_ai.apply_clothing')
    async def test_apply_clothing_success(self, mock_apply, client, user_headers):
        """Test applying clothing to image"""
        mock_apply.return_value = "https://example.com/applied.jpg"

        apply_data = {
            "person_image_url": "https://example.com/person.jpg",
            "clothing_image_url": "https://example.com/clothing.jpg"
        }

        response = client.post(
            "/api/v1/generations/apply-clothing",
            headers=user_headers,
            json=apply_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_apply_clothing_unauthorized(self, client):
        """Test apply clothing without auth"""
        apply_data = {
            "person_image_url": "https://example.com/person.jpg",
            "clothing_image_url": "https://example.com/clothing.jpg"
        }

        response = client.post("/api/v1/generations/apply-clothing", json=apply_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Generate Person Tests
    @pytest.mark.asyncio
    @patch('app.core.gemini.gemini_ai.generate_person')
    async def test_generate_person_success(self, mock_generate, client, user_headers):
        """Test generating person image"""
        mock_generate.return_value = "https://example.com/person.jpg"

        person_data = {
            "prompt": "young woman with long hair"
        }

        response = client.post(
            "/api/v1/generations/generate-person",
            headers=user_headers,
            json=person_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    # Generate Clothing Tests
    @pytest.mark.asyncio
    @patch('app.core.gemini.gemini_ai.generate_clothing')
    async def test_generate_clothing_success(self, mock_generate, client, user_headers):
        """Test generating clothing image"""
        mock_generate.return_value = "https://example.com/clothing.jpg"

        clothing_data = {
            "prompt": "red summer dress"
        }

        response = client.post(
            "/api/v1/generations/generate-clothing",
            headers=user_headers,
            json=clothing_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    # Base64 Image Tests
    @pytest.mark.asyncio
    @patch('app.core.gemini.gemini_ai.apply_clothing_base64')
    async def test_apply_clothing_base64_success(self, mock_apply, client, user_headers):
        """Test applying clothing with base64 images"""
        mock_apply.return_value = "https://example.com/result.jpg"

        apply_data = {
            "person_image_base64": "base64_person_data",
            "clothing_image_base64": "base64_clothing_data"
        }

        response = client.post(
            "/api/v1/generations/apply-clothing-base64",
            headers=user_headers,
            json=apply_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    # Text to Image Tests
    @pytest.mark.asyncio
    @patch('app.core.gemini.gemini_ai.generate_image_from_text')
    async def test_generate_image_from_text(self, mock_generate, client, user_headers):
        """Test generating image from text"""
        mock_generate.return_value = "https://example.com/generated.jpg"

        text_data = {
            "prompt": "beautiful sunset over mountains"
        }

        response = client.post(
            "/api/v1/generations/generate-from-text",
            headers=user_headers,
            json=text_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    # Text and Images to Image Tests
    @pytest.mark.asyncio
    @patch('app.core.gemini.gemini_ai.generate_image_from_text_and_images')
    async def test_generate_from_text_and_images(self, mock_generate, client, user_headers):
        """Test generating image from text and images"""
        mock_generate.return_value = "https://example.com/combined.jpg"

        combined_data = {
            "prompt": "combine these elements",
            "image_urls": [
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg"
            ]
        }

        response = client.post(
            "/api/v1/generations/generate-from-text-and-images",
            headers=user_headers,
            json=combined_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    # Edge Cases
    @pytest.mark.asyncio
    async def test_generate_with_very_long_prompt(self, client, user_headers):
        """Test generation with very long prompt"""
        generation_data = {
            "prompt": "a" * 10000  # Very long prompt
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=user_headers,
            json=generation_data
        )

        # Should either accept or reject based on limits
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_402_PAYMENT_REQUIRED
        ]

    @pytest.mark.asyncio
    async def test_generate_with_special_characters(self, client, user_headers):
        """Test generation with special characters in prompt"""
        generation_data = {
            "prompt": "dress with 💃 emoji and special chars !@#$%"
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=user_headers,
            json=generation_data
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_402_PAYMENT_REQUIRED
        ]

    @pytest.mark.asyncio
    @patch('app.services.generation_service.generation_service.generate_fashion')
    @patch('app.services.user_service.user_service.charge_for_generation')
    async def test_generation_with_free_credits(self, mock_charge, mock_generate, client, user_headers, test_user):
        """Test generation using free credits"""
        mock_charge.return_value = {"amount": 0.0, "method": "free_credit"}
        mock_generate.return_value = MagicMock(
            id=1,
            user_id=test_user.id,
            prompt="test",
            image_url="https://example.com/test.jpg",
            cost=0.0
        )

        generation_data = {
            "prompt": "test prompt"
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=user_headers,
            json=generation_data
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_shop_cannot_generate(self, client, shop_headers):
        """Test that shops cannot access generation endpoints"""
        generation_data = {
            "prompt": "test"
        }

        response = client.post(
            "/api/v1/generations/generate",
            headers=shop_headers,
            json=generation_data
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
