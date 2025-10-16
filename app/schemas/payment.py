from pydantic import BaseModel, Field
from typing import Optional, Dict


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    payment_type: str  # "top_up", "product_rent", "product_purchase"
    extra_data: Optional[Dict] = None


class PaymentResponse(BaseModel):
    order_id: str
    approval_url: str
    amount: float
    status: str


class PayPalWebhook(BaseModel):
    event_type: str
    resource: Dict

    model_config = {"extra": "allow"}  # Allow extra fields from PayPal
