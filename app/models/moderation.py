from __future__ import annotations

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class ModerationQueue(Base):
    __tablename__ = "moderation_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="moderation_queue")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<ModerationQueue(id={self.id}, product_id={self.product_id})>"
