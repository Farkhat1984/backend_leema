"""
Wardrobe model - User's clothing collection for analytics
Track what users try on and save to analyze fashion trends
"""
from __future__ import annotations

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
import enum
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.generation import Generation
    from app.models.user import User


class WardrobeItemSource(str, enum.Enum):
    """Where the wardrobe item came from"""
    SHOP_PRODUCT = "shop_product"      # Copied from shop
    GENERATED = "generated"             # AI generated
    UPLOADED = "uploaded"               # User uploaded
    PURCHASED = "purchased"             # Bought from shop


class UserWardrobeItem(Base):
    """
    User's personal wardrobe item
    Used for analytics: what users save, what's popular, fashion trends
    """
    __tablename__ = "user_wardrobe_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source: Mapped[WardrobeItemSource] = mapped_column(SQLEnum(WardrobeItemSource), nullable=False, index=True)
    
    # References to source items (for analytics)
    original_product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )
    generation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("generations.id"), nullable=True, index=True
    )
    
    # Item data (user can edit)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # URLs
    characteristics: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Size, color, etc.
    
    # Analytics metadata
    is_favorite: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    folder: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wardrobe_items")
    original_product: Mapped["Product"] = relationship("Product", foreign_keys=[original_product_id])
    generation: Mapped["Generation"] = relationship("Generation", foreign_keys=[generation_id])

    def __repr__(self):
        return f"<WardrobeItem(id={self.id}, user_id={self.user_id}, source={self.source})>"
