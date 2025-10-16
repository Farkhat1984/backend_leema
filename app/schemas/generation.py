from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from datetime import datetime
from typing import Optional, Any


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class GenerationBase(CamelModel):
    type: str
    cost: float


class GenerationCreate(GenerationBase):
    user_id: int
    product_id: Optional[int] = None
    image_url: Optional[str] = None


class GenerationRequest(CamelModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    user_image_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("user_image_url", "userImageUrl")
    )  # URL загруженного фото пользователя


class TryOnRequest(CamelModel):
    product_id: int = Field(..., gt=0)
    user_image_url: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("user_image_url", "userImageUrl")
    )  # URL загруженного фото пользователя


class ApplyClothingRequest(CamelModel):
    clothing_image_url: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("clothing_image_url", "clothingImageUrl")
    )  # URL изображения одежды
    person_image_url: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("person_image_url", "personImageUrl")
    )  # URL изображения модели/пользователя


# New Gemini 2.5 Flash Image API schemas
class GeneratePersonRequest(CamelModel):
    """Generate a person/model image from text description"""
    description: str = Field(..., min_length=1, max_length=1000, description="Description of the person to generate")
    aspect_ratio: str = Field(
        default="2:3",
        description="Image aspect ratio (e.g., '1:1', '2:3', '16:9')",
        validation_alias=AliasChoices("aspect_ratio", "aspectRatio")
    )


class GenerateClothingRequest(CamelModel):
    """Generate clothing image from text description"""
    description: str = Field(..., min_length=1, max_length=1000, description="Description of the clothing to generate")
    aspect_ratio: str = Field(
        default="1:1",
        description="Image aspect ratio",
        validation_alias=AliasChoices("aspect_ratio", "aspectRatio")
    )


class ApplyClothingBase64Request(CamelModel):
    """Apply clothing to model using base64 images"""
    person_base64: str = Field(
        ...,
        min_length=1,
        description="Base64 encoded person/model image",
        validation_alias=AliasChoices("person_base64", "personBase64")
    )
    clothing_base64: Optional[str] = Field(
        None,
        description="Base64 encoded clothing image (optional)",
        validation_alias=AliasChoices("clothing_base64", "clothingBase64")
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Description of clothing to apply (if clothing_base64 not provided)"
    )
    aspect_ratio: str = Field(
        default="2:3",
        description="Output image aspect ratio",
        validation_alias=AliasChoices("aspect_ratio", "aspectRatio")
    )


class GenerateImageFromTextRequest(CamelModel):
    """Generate image from text prompt using Gemini 2.5 Flash Image"""
    prompt: str = Field(..., min_length=1, max_length=2000, description="Text prompt for image generation")
    aspect_ratio: str = Field(
        default="1:1",
        description="Image aspect ratio (1:1, 2:3, 3:2, 4:3, 3:4, 16:9, 9:16)",
        validation_alias=AliasChoices("aspect_ratio", "aspectRatio")
    )


class GenerateImageFromTextAndImagesRequest(CamelModel):
    """Generate image from text and reference images"""
    prompt: str = Field(..., min_length=1, max_length=2000, description="Text prompt")
    images_base64: list[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="List of base64 encoded images (1-5 images)",
        validation_alias=AliasChoices("images_base64", "images", "imagesBase64")
    )
    aspect_ratio: str = Field(
        default="1:1",
        description="Output image aspect ratio",
        validation_alias=AliasChoices("aspect_ratio", "aspectRatio")
    )


class GenerationResponse(GenerationBase):
    id: int
    user_id: int
    product_id: Optional[int] = None
    image_url: Optional[str] = None
    created_at: datetime
    charge_info: Optional[dict] = None  # Information about charge

    model_config = {"from_attributes": True}
