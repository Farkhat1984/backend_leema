from __future__ import annotations

from sqlalchemy import String, Integer, Numeric, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
import enum
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.generation import Generation
    from app.models.order import Order
    from app.models.refund import Refund
    from app.models.transaction import Transaction
    from app.models.cart import Cart
    from app.models.wardrobe import UserWardrobeItem


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    apple_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    free_generations_left: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_try_ons_left: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", foreign_keys="Transaction.user_id"
    )
    generations: Mapped[list["Generation"]] = relationship("Generation", back_populates="user")
    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="user")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    cart: Mapped["Cart"] = relationship("Cart", back_populates="user", uselist=False)
    wardrobe_items: Mapped[list["UserWardrobeItem"]] = relationship("UserWardrobeItem", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
