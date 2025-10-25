from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any, Dict

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.generation_service import generation_service
from app.schemas.generation import (
    GenerationRequest, TryOnRequest, ApplyClothingRequest, GenerationResponse,
    GeneratePersonRequest, GenerateClothingRequest, ApplyClothingBase64Request,
    GenerateImageFromTextRequest, GenerateImageFromTextAndImagesRequest
)
from app.core.gemini import gemini_ai

router = APIRouter()


def _camelize_key(key: str) -> str:
    parts = key.split('_')
    if not parts:
        return key
    return parts[0] + ''.join(part.capitalize() for part in parts[1:])


def _format_image_response(image_url: str, **payload: Any) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "success": True,
        "image_url": image_url,
        "imageUrl": image_url,
    }

    for key, value in payload.items():
        if value is None:
            continue
        response[key] = value
        camel_key = _camelize_key(key)
        response[camel_key] = value

    return response


@router.post("/generate", response_model=GenerationResponse)
async def generate_fashion(
    request: GenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate fashion based on prompt - charges user"""
    from app.services.user_service import user_service

    try:
        # Charge user before generation
        charge_info = await user_service.charge_for_generation(db, current_user.id)

        # Generate fashion
        generation = await generation_service.generate_fashion(
            db,
            current_user.id,
            request.prompt,
            request.user_image_url,
            cost=charge_info.get("amount", 0.0)
        )

        if not generation:
            raise HTTPException(
                status_code=400,
                detail="Failed to generate fashion. Try again."
            )

        # Add charge info to response
        response = GenerationResponse.model_validate(generation)
        response.charge_info = charge_info
        return response

    except ValueError as e:
        # Insufficient balance or credits
        raise HTTPException(status_code=402, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions (like the 400 from above)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")


@router.post("/try-on", response_model=GenerationResponse)
async def try_on_product(
    request: TryOnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Try on product on user image - charges user"""
    from app.services.user_service import user_service

    try:
        # Charge user before try-on
        charge_info = await user_service.charge_for_tryon(db, current_user.id)

        # Generate try-on (with optional wardrobe save)
        generation, wardrobe_item_id = await generation_service.try_on_product(
            db,
            current_user.id,
            request.product_id,
            request.user_image_url,
            cost=charge_info.get("amount", 0.0),
            save_to_wardrobe=request.save_to_wardrobe
        )

        if not generation:
            raise HTTPException(
                status_code=400,
                detail="Failed to generate try-on. Try again."
            )

        # Add charge info and wardrobe ID to response
        response = GenerationResponse.model_validate(generation)
        response.charge_info = charge_info
        response.wardrobe_item_id = wardrobe_item_id
        return response

    except ValueError as e:
        # Insufficient balance or credits
        raise HTTPException(status_code=402, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions (like the 400 from above)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Try-on error: {str(e)}")


@router.post("/apply-clothing", response_model=GenerationResponse)
async def apply_clothing_to_model(
    request: ApplyClothingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply clothing from image to model image - charges user like try-on"""
    from app.services.user_service import user_service

    try:
        # Charge user before applying (same as try-on)
        charge_info = await user_service.charge_for_tryon(db, current_user.id)

        # Apply clothing to model
        generation = await generation_service.apply_clothing_to_model(
            db,
            current_user.id,
            request.clothing_image_url,
            request.person_image_url,
            cost=charge_info.get("amount", 0.0)
        )

        if not generation:
            raise HTTPException(
                status_code=400,
                detail="Failed to apply clothing to model. Try again."
            )

        # Add charge info to response
        response = GenerationResponse.model_validate(generation)
        response.charge_info = charge_info
        return response

    except ValueError as e:
        # Insufficient balance or credits
        raise HTTPException(status_code=402, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions (like the 400 from above)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply clothing error: {str(e)}")


@router.delete("/{generation_id}")
async def delete_generation(
    generation_id: int,
    delete_files: bool = Query(True, description="Delete associated image files"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete generation
    
    Cannot delete if generation is saved in wardrobe.
    Remove from wardrobe first.
    
    **Path parameters:**
    - generation_id: ID of the generation to delete
    
    **Query parameters:**
    - delete_files: If true, deletes image files (default: true)
    """
    deleted = await generation_service.delete_generation(
        db, generation_id, current_user.id, delete_files=delete_files
    )
    
    if not deleted:
        # Check if it exists but is in use
        from app.models.wardrobe import UserWardrobeItem
        wardrobe_result = await db.execute(
            select(func.count(UserWardrobeItem.id))
            .where(UserWardrobeItem.generation_id == generation_id)
        )
        wardrobe_count = wardrobe_result.scalar() or 0
        
        if wardrobe_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete: generation is saved in {wardrobe_count} wardrobe item(s). Remove from wardrobe first."
            )
        
        raise HTTPException(
            status_code=404,
            detail="Generation not found"
        )
    
    return {"message": "Generation deleted successfully", "id": generation_id}


# New Gemini 2.5 Flash Image endpoints
# Append this to generations.py or use as reference

@router.post("/generate-person")
async def generate_person_image(
    request: GeneratePersonRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a person/model image from text description
    Uses Gemini 2.5 Flash Image model
    """
    try:
        image_url = await gemini_ai.generate_person(
            description=request.description,
            aspect_ratio=request.aspect_ratio
        )

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate person image"
            )
        return _format_image_response(
            image_url,
            description=request.description,
            aspect_ratio=request.aspect_ratio
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Person generation error: {str(e)}"
        )


@router.post("/generate-clothing")
async def generate_clothing_image(
    request: GenerateClothingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate clothing image from text description
    Uses Gemini 2.5 Flash Image model
    """
    try:
        image_url = await gemini_ai.generate_clothing(
            description=request.description,
            aspect_ratio=request.aspect_ratio
        )

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate clothing image"
            )
        return _format_image_response(
            image_url,
            description=request.description,
            aspect_ratio=request.aspect_ratio
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Clothing generation error: {str(e)}"
        )


@router.post("/apply-clothing-base64")
async def apply_clothing_base64(
    request: ApplyClothingBase64Request,
    current_user: User = Depends(get_current_user)
):
    """
    Apply clothing to model using base64 encoded images
    Supports both clothing image OR text description
    Uses Gemini 2.5 Flash Image model
    """
    try:
        image_url = await gemini_ai.apply_clothing_base64(
            person_base64=request.person_base64,
            clothing_base64=request.clothing_base64,
            description=request.description,
            aspect_ratio=request.aspect_ratio
        )

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to apply clothing to model"
            )
        return _format_image_response(
            image_url,
            aspect_ratio=request.aspect_ratio,
            description=request.description,
            input_mode="clothing_image" if request.clothing_base64 else "description"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Apply clothing error: {str(e)}"
        )


@router.post("/generate-from-text")
async def generate_image_from_text(
    request: GenerateImageFromTextRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate image from text prompt
    Uses Gemini 2.5 Flash Image model
    Supports various aspect ratios
    """
    try:
        image_url = await gemini_ai.generate_image_from_text(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio
        )

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate image from text"
            )
        return _format_image_response(
            image_url,
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Text to image error: {str(e)}"
        )


@router.post("/generate-from-text-and-images")
async def generate_image_from_text_and_images(
    request: GenerateImageFromTextAndImagesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate image from text prompt and reference images
    Uses Gemini 2.5 Flash Image model
    Accepts 1-5 reference images as base64
    """
    try:
        image_url = await gemini_ai.generate_image_from_text_and_images(
            prompt=request.prompt,
            images_base64=request.images_base64,
            aspect_ratio=request.aspect_ratio
        )

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate image from text and images"
            )
        return _format_image_response(
            image_url,
            prompt=request.prompt,
            reference_images_count=len(request.images_base64),
            aspect_ratio=request.aspect_ratio
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Text+images to image error: {str(e)}"
        )
