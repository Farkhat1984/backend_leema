from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any


class GenerationBase(BaseModel):
    type: str
    cost: float


class GenerationCreate(GenerationBase):
    user_id: int
    product_id: Optional[int] = None
    image_url: Optional[str] = None


class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    user_image_url: Optional[str] = None  # URL загруженного фото пользователя


class TryOnRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    user_image_url: str = Field(..., min_length=1)  # URL загруженного фото пользователя


class ApplyClothingRequest(BaseModel):
    clothing_image_url: str = Field(..., min_length=1)  # URL изображения одежды
    person_image_url: str = Field(..., min_length=1)  # URL изображения модели/пользователя


class GenerationResponse(GenerationBase):
    id: int
    user_id: int
    product_id: Optional[int] = None
    image_url: Optional[str] = None
    created_at: datetime
    charge_info: Optional[dict] = None  # Information about charge

    model_config = {"from_attributes": True}
