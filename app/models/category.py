"""
Product Categories - Admin managed categories for fashion items
Used for filtering, search, and analytics
"""
from __future__ import annotations

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
from app.database import Base
from app.core.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.product import Product


class ProductCategory(Base):
    """
    Product categories managed by admin
    Examples: Dresses, Shirts, Pants, Shoes, Accessories
    """
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Hierarchy support (optional)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("product_categories.id"), nullable=True)
    
    # Display order
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Active/Inactive
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")
    parent: Mapped["ProductCategory"] = relationship("ProductCategory", remote_side=[id], foreign_keys=[parent_id])

    def __repr__(self):
        return f"<ProductCategory(id={self.id}, name={self.name})>"
