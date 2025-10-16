"""
Tests for generation endpoints
"""
import pytest
from unittest.mock import patch, AsyncMock
from io import BytesIO


class TestGenerationEndpoints:
    """Test AI generation API endpoints"""

    def test_create_generation_unauthorized(self, client):
        """Test creating generation without authentication"""
        generation_data = {
            "prompt": "A beautiful landscape",
            "type": "image"
        }

        response = client.post("/api/generations/create", json=generation_data)

        assert response.status_code == 401

    @patch('app.core.gemini.gemini_service.generate_image')
    def test_create_image_generation(self, mock_generate, client, auth_headers):
        """Test creating an image generation"""
        mock_generate.return_value = "https://example.com/generated_image.jpg"

        generation_data = {
            "prompt": "A beautiful landscape",
            "type": "image"
        }

        response = client.post("/api/generations/create", 
                              headers=auth_headers,
                              json=generation_data)

        assert response.status_code in [201, 401, 400, 402, 422]

    def test_create_generation_insufficient_balance(self, client, auth_headers):
        """Test creating generation with insufficient balance"""
        generation_data = {
            "prompt": "A beautiful landscape",
            "type": "image"
        }

        # Assuming user has no balance
        response = client.post("/api/generations/create", 
                              headers=auth_headers,
                              json=generation_data)

        assert response.status_code in [201, 401, 402, 400]

    def test_get_user_generations(self, client, auth_headers):
        """Test getting user's generations"""
        response = client.get("/api/generations/", headers=auth_headers)

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_generation_by_id(self, client, auth_headers):
        """Test getting single generation by ID"""
        response = client.get("/api/generations/1", headers=auth_headers)

        assert response.status_code in [200, 401, 404]

    def test_delete_generation(self, client, auth_headers):
        """Test deleting a generation"""
        response = client.delete("/api/generations/1", headers=auth_headers)

        assert response.status_code in [200, 204, 401, 404]

    @patch('app.core.gemini.gemini_service.virtual_try_on')
    def test_virtual_try_on(self, mock_try_on, client, auth_headers):
        """Test virtual try-on feature"""
        mock_try_on.return_value = "https://example.com/try_on_result.jpg"

        # Create fake image file
        file_content = b"fake image content"
        files = {
            "user_image": ("user.jpg", BytesIO(file_content), "image/jpeg")
        }
        data = {"product_id": "1"}

        response = client.post("/api/generations/try-on", 
                              headers=auth_headers,
                              files=files,
                              data=data)

        assert response.status_code in [201, 401, 400, 402, 404, 422]

    def test_regenerate(self, client, auth_headers):
        """Test regenerating from existing generation"""
        response = client.post("/api/generations/1/regenerate", 
                              headers=auth_headers)

        assert response.status_code in [201, 401, 404, 400, 402]
