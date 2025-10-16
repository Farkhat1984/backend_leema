"""Order model for tracking purchases and rentals"""
from __future__ import annotations

from sqlalchemy import String, Integer, Numeric, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
import enum
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
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), nullable=False)
    
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
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

    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, type={self.order_type})>"
