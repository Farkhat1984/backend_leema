from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class TransactionBase(BaseModel):
    type: str
    amount: float


class TransactionCreate(TransactionBase):
    user_id: Optional[int] = None
    shop_id: Optional[int] = None
    extra_data: Optional[Dict] = None


class TransactionResponse(TransactionBase):
    id: int
    user_id: Optional[int] = None
    shop_id: Optional[int] = None
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    status: str
    extra_data: Optional[Dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer('type', 'status', when_used='always')
    def serialize_enum(self, value):
        """Convert enum to string value"""
        if hasattr(value, 'value'):
            return value.value
        return str(value) if value else value


class TransactionList(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int
