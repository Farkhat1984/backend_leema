from __future__ import annotations

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
import enum
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class GenerationType(str, enum.Enum):
    GENERATION = "generation"  # Генерация одежды
    TRY_ON = "try_on"  # Примерка товара


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    type: Mapped[GenerationType] = mapped_column(Enum(GenerationType), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="generations")
    product: Mapped["Product"] = relationship("Product", back_populates="generations")

    def __repr__(self):
        return f"<Generation(id={self.id}, type={self.type}, user_id={self.user_id})>"
