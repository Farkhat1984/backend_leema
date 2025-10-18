"""
WebSocket Event Schemas

Defines all webhook event types and their payloads
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum


class WebhookEventType(str, Enum):
    """Types of webhook events"""
    # Product events
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_DELETED = "product.deleted"
    PRODUCT_APPROVED = "product.approved"
    PRODUCT_REJECTED = "product.rejected"

    # Balance events
    BALANCE_UPDATED = "balance.updated"

    # Transaction events
    TRANSACTION_COMPLETED = "transaction.completed"
    TRANSACTION_FAILED = "transaction.failed"

    # Order events
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"

    # Review events
    REVIEW_CREATED = "review.created"

    # Settings events
    SETTINGS_UPDATED = "settings.updated"

    # Moderation events
    MODERATION_QUEUE_UPDATED = "moderation.queue_updated"


class WebhookEvent(BaseModel):
    """Base webhook event"""
    event: WebhookEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Product Events

class ProductModerationEventData(BaseModel):
    """Product moderation event data"""
    product_id: int
    product_name: str
    shop_id: int
    shop_name: Optional[str] = None
    moderation_status: str  # approved, rejected
    moderation_notes: Optional[str] = None
    admin_id: int
    approval_fee: Optional[float] = None  # For approved products
    # Full product data for mobile apps
    product: Optional[Dict[str, Any]] = None


class ProductEventData(BaseModel):
    """Product CRUD event data"""
    product_id: int
    product_name: str
    shop_id: int
    action: str  # created, updated, deleted
    moderation_status: Optional[str] = None
    is_active: Optional[bool] = None
    # Full product data for mobile apps
    product: Optional[Dict[str, Any]] = None


# Balance Events

class BalanceUpdateEventData(BaseModel):
    """Balance update event data"""
    entity_type: str  # user, shop
    entity_id: int
    old_balance: float
    new_balance: float
    change_amount: float
    transaction_id: Optional[int] = None
    reason: Optional[str] = None


# Transaction Events

class TransactionEventData(BaseModel):
    """Transaction event data"""
    transaction_id: int
    transaction_type: str
    amount: float
    status: str  # completed, failed
    user_id: Optional[int] = None
    shop_id: Optional[int] = None
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


# Order Events

class OrderEventData(BaseModel):
    """Order event data"""
    order_id: int
    order_type: str  # purchase, rental
    status: str
    user_id: int
    shop_id: int
    product_id: int
    product_name: str
    amount: float
    quantity: int


# Review Events

class ReviewEventData(BaseModel):
    """Review event data"""
    review_id: int
    product_id: int
    product_name: str
    shop_id: int
    user_id: int
    user_name: str
    rating: int
    comment: Optional[str] = None


# Settings Events

class SettingsUpdateEventData(BaseModel):
    """Settings update event data"""
    key: str
    old_value: Optional[str] = None
    new_value: str
    description: Optional[str] = None
    updated_by: int  # admin_id


# Moderation Events

class ModerationQueueEventData(BaseModel):
    """Moderation queue event data"""
    pending_count: int
    action: str  # added, processed
    product_id: Optional[int] = None


# Helper functions to create events

def create_product_moderation_event(
    event_type: WebhookEventType,
    product_id: int,
    product_name: str,
    shop_id: int,
    moderation_status: str,
    admin_id: int,
    shop_name: Optional[str] = None,
    moderation_notes: Optional[str] = None,
    approval_fee: Optional[float] = None,
    product: Optional[Dict[str, Any]] = None
) -> WebhookEvent:
    """Create product moderation event"""
    return WebhookEvent(
        event=event_type,
        data=ProductModerationEventData(
            product_id=product_id,
            product_name=product_name,
            shop_id=shop_id,
            shop_name=shop_name,
            moderation_status=moderation_status,
            moderation_notes=moderation_notes,
            admin_id=admin_id,
            approval_fee=approval_fee,
            product=product
        ).model_dump()
    )


def create_product_event(
    event_type: WebhookEventType,
    product_id: int,
    product_name: str,
    shop_id: int,
    action: str,
    moderation_status: Optional[str] = None,
    is_active: Optional[bool] = None,
    product: Optional[Dict[str, Any]] = None
) -> WebhookEvent:
    """Create product CRUD event"""
    return WebhookEvent(
        event=event_type,
        data=ProductEventData(
            product_id=product_id,
            product_name=product_name,
            shop_id=shop_id,
            action=action,
            moderation_status=moderation_status,
            is_active=is_active,
            product=product
        ).model_dump()
    )


def create_balance_update_event(
    entity_type: str,
    entity_id: int,
    old_balance: float,
    new_balance: float,
    transaction_id: Optional[int] = None,
    reason: Optional[str] = None
) -> WebhookEvent:
    """Create balance update event"""
    return WebhookEvent(
        event=WebhookEventType.BALANCE_UPDATED,
        data=BalanceUpdateEventData(
            entity_type=entity_type,
            entity_id=entity_id,
            old_balance=old_balance,
            new_balance=new_balance,
            change_amount=new_balance - old_balance,
            transaction_id=transaction_id,
            reason=reason
        ).model_dump()
    )


def create_transaction_event(
    event_type: WebhookEventType,
    transaction_id: int,
    transaction_type: str,
    amount: float,
    status: str,
    user_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    description: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> WebhookEvent:
    """Create transaction event"""
    return WebhookEvent(
        event=event_type,
        data=TransactionEventData(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=amount,
            status=status,
            user_id=user_id,
            shop_id=shop_id,
            description=description,
            extra_data=extra_data
        ).model_dump()
    )


def create_order_event(
    event_type: WebhookEventType,
    order_id: int,
    order_type: str,
    status: str,
    user_id: int,
    shop_id: int,
    product_id: int,
    product_name: str,
    amount: float,
    quantity: int
) -> WebhookEvent:
    """Create order event"""
    return WebhookEvent(
        event=event_type,
        data=OrderEventData(
            order_id=order_id,
            order_type=order_type,
            status=status,
            user_id=user_id,
            shop_id=shop_id,
            product_id=product_id,
            product_name=product_name,
            amount=amount,
            quantity=quantity
        ).model_dump()
    )


def create_review_event(
    review_id: int,
    product_id: int,
    product_name: str,
    shop_id: int,
    user_id: int,
    user_name: str,
    rating: int,
    comment: Optional[str] = None
) -> WebhookEvent:
    """Create review event"""
    return WebhookEvent(
        event=WebhookEventType.REVIEW_CREATED,
        data=ReviewEventData(
            review_id=review_id,
            product_id=product_id,
            product_name=product_name,
            shop_id=shop_id,
            user_id=user_id,
            user_name=user_name,
            rating=rating,
            comment=comment
        ).model_dump()
    )


def create_settings_update_event(
    key: str,
    new_value: str,
    updated_by: int,
    old_value: Optional[str] = None,
    description: Optional[str] = None
) -> WebhookEvent:
    """Create settings update event"""
    return WebhookEvent(
        event=WebhookEventType.SETTINGS_UPDATED,
        data=SettingsUpdateEventData(
            key=key,
            old_value=old_value,
            new_value=new_value,
            description=description,
            updated_by=updated_by
        ).model_dump()
    )


def create_moderation_queue_event(
    pending_count: int,
    action: str,
    product_id: Optional[int] = None
) -> WebhookEvent:
    """Create moderation queue event"""
    return WebhookEvent(
        event=WebhookEventType.MODERATION_QUEUE_UPDATED,
        data=ModerationQueueEventData(
            pending_count=pending_count,
            action=action,
            product_id=product_id
        ).model_dump()
    )
