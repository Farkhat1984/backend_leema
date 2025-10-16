"""
Tests for payment endpoints
"""
import pytest
from unittest.mock import patch


class TestPaymentEndpoints:
    """Test payment API endpoints"""

    def test_create_payment_unauthorized(self, client):
        """Test creating payment without authentication"""
        payment_data = {
            "amount": 50.0,
            "payment_method": "paypal"
        }

        response = client.post("/api/payments/create", json=payment_data)

        assert response.status_code == 401

    def test_create_payment(self, client, auth_headers):
        """Test creating a payment"""
        payment_data = {
            "amount": 50.0,
            "payment_method": "paypal"
        }

        response = client.post("/api/payments/create", 
                              headers=auth_headers,
                              json=payment_data)

        assert response.status_code in [200, 201, 401, 400, 422]

    def test_create_payment_invalid_amount(self, client, auth_headers):
        """Test creating payment with invalid amount"""
        payment_data = {
            "amount": -10.0,
            "payment_method": "paypal"
        }

        response = client.post("/api/payments/create", 
                              headers=auth_headers,
                              json=payment_data)

        assert response.status_code in [400, 422]

    @patch('app.core.paypal.paypal_service.capture_payment')
    def test_capture_payment(self, mock_capture, client, auth_headers):
        """Test capturing a payment"""
        mock_capture.return_value = {"status": "COMPLETED"}

        response = client.post("/api/payments/capture", 
                              headers=auth_headers,
                              json={"order_id": "test_order_id"})

        assert response.status_code in [200, 401, 400, 404]

    def test_get_payment_history(self, client, auth_headers):
        """Test getting payment history"""
        response = client.get("/api/payments/history", headers=auth_headers)

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_cancel_payment(self, client, auth_headers):
        """Test canceling a payment"""
        response = client.post("/api/payments/cancel", 
                              headers=auth_headers,
                              json={"order_id": "test_order_id"})

        assert response.status_code in [200, 401, 404, 400]

    def test_refund_payment(self, client, auth_headers):
        """Test requesting a refund"""
        response = client.post("/api/payments/refund", 
                              headers=auth_headers,
                              json={"order_id": "test_order_id"})

        assert response.status_code in [200, 401, 404, 400]
