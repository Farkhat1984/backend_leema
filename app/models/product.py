from __future__ import annotations

from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from datetime import datetime
import enum
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.generation import Generation
    from app.models.moderation import ModerationQueue
    from app.models.order import Order
    from app.models.review import Review
    from app.models.shop import Shop


class ModerationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    characteristics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Array of URLs
    rent_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus), default=ModerationStatus.PENDING, nullable=False
    )
    moderation_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    try_ons_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="products")
    generations: Mapped[list["Generation"]] = relationship("Generation", back_populates="product")
    moderation_queue: Mapped["ModerationQueue"] = relationship(
        "ModerationQueue", back_populates="product", uselist=False, cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="product")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product")

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, shop_id={self.shop_id})>"
