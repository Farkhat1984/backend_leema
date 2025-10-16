"""Review schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # User info
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

    model_config = {"from_attributes": True}
