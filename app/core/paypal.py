from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest, OrdersGetRequest
from paypalhttp import HttpError
from app.config import settings
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class PayPalClient:
    """PayPal payment handler"""

    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET

        if settings.PAYPAL_MODE == "live":
            environment = LiveEnvironment(client_id=self.client_id, client_secret=self.client_secret)
        else:
            environment = SandboxEnvironment(client_id=self.client_id, client_secret=self.client_secret)

        self.client = PayPalHttpClient(environment)

    async def create_order(self, amount: float, currency: str = "USD", description: str = "", platform: str = "web") -> Optional[Dict]:
        """Create PayPal order"""
        try:
            # Determine return URLs based on platform
            if platform == "mobile":
                return_url = f"{settings.API_BASE_URL}/api/payments/paypal/success?platform=mobile"
                cancel_url = f"{settings.API_BASE_URL}/api/payments/paypal/cancel?platform=mobile"
            else:
                return_url = f"{settings.API_BASE_URL}/api/payments/paypal/success?platform=web"
                cancel_url = f"{settings.API_BASE_URL}/api/payments/paypal/cancel?platform=web"
            
            request = OrdersCreateRequest()
            request.prefer("return=representation")
            request.request_body({
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": currency,
                            "value": str(amount)
                        },
                        "description": description
                    }
                ],
                "application_context": {
                    "brand_name": settings.APP_NAME,
                    "landing_page": "BILLING",
                    "user_action": "PAY_NOW",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                }
            })

            response = self.client.execute(request)

            # Get approval URL
            approval_url = None
            for link in response.result.links:
                if link.rel == "approve":
                    approval_url = link.href
                    break

            return {
                "order_id": response.result.id,
                "status": response.result.status,
                "approval_url": approval_url,
                "amount": amount,
            }
        except HttpError as e:
            logger.error(f"PayPal create order error: {e}")
            return None

    async def capture_order(self, order_id: str) -> Optional[Dict]:
        """Capture (complete) PayPal order"""
        try:
            request = OrdersCaptureRequest(order_id)
            response = self.client.execute(request)

            capture_id = response.result.purchase_units[0].payments.captures[0].id
            amount = response.result.purchase_units[0].payments.captures[0].amount.value

            return {
                "order_id": order_id,
                "capture_id": capture_id,
                "status": response.result.status,
                "amount": float(amount),
            }
        except HttpError as e:
            logger.error(f"PayPal capture order error: {e}")
            return None

    async def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details"""
        try:
            request = OrdersGetRequest(order_id)
            response = self.client.execute(request)

            return {
                "order_id": response.result.id,
                "status": response.result.status,
                "amount": float(response.result.purchase_units[0].amount.value),
            }
        except HttpError as e:
            logger.error(f"PayPal get order error: {e}")
            return None


paypal_client = PayPalClient()
