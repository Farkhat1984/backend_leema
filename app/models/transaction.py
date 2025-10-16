from __future__ import annotations

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
import enum
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.refund import Refund
    from app.models.shop import Shop
    from app.models.user import User


class TransactionType(str, enum.Enum):
    TOP_UP = "TOP_UP"  # Пополнение баланса пользователя
    GENERATION = "GENERATION"  # Списание за генерацию
    TRY_ON = "TRY_ON"  # Списание за примерку
    PRODUCT_RENT = "PRODUCT_RENT"  # Оплата аренды товара магазином
    PRODUCT_PURCHASE = "PRODUCT_PURCHASE"  # Покупа товара пользователем
    REFUND = "REFUND"  # Возврат средств
    COMMISSION = "COMMISSION"  # Комиссия платформы
    APPROVAL_FEE = "APPROVAL_FEE"  # Плата за одобрение товара админом


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    shop_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("shops.id"), nullable=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    paypal_order_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    paypal_capture_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False
    )
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    shop: Mapped["Shop"] = relationship("Shop", back_populates="transactions", foreign_keys=[shop_id])
    refund: Mapped["Refund"] = relationship("Refund", back_populates="transaction", uselist=False)
    order: Mapped["Order"] = relationship("Order", back_populates="transaction", uselist=False)

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount}, status={self.status})>"
