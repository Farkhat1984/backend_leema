"""Order model for tracking purchases and rentals"""
from __future__ import annotations

from sqlalchemy import String, Integer, Numeric, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
import enum
import secrets
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.shop import Shop
    from app.models.transaction import Transaction
    from app.models.user import User


class OrderType(str, enum.Enum):
    PURCHASE = "purchase"
    RENTAL = "rental"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Legacy fields for backwards compatibility (will be deprecated)
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    shop_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("shops.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.PURCHASE, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    # For rentals
    rental_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rental_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rental_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    transaction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    shop: Mapped["Shop"] = relationship("Shop", back_populates="orders")
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="order", uselist=False)
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number like ORD-20251018-XXXXX"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = secrets.token_hex(3).upper()
        return f"ORD-{date_str}-{random_str}"

    def __repr__(self):
        return f"<Order(id={self.id}, order_number={self.order_number}, user_id={self.user_id})>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_purchase: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
    shop: Mapped["Shop"] = relationship("Shop")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"
