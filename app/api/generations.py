from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.generation_service import generation_service
from app.schemas.generation import GenerationRequest, TryOnRequest, ApplyClothingRequest, GenerationResponse

router = APIRouter()


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

        # Generate try-on
        generation = await generation_service.try_on_product(
            db,
            current_user.id,
            request.product_id,
            request.user_image_url,
            cost=charge_info.get("amount", 0.0)
        )

        if not generation:
            raise HTTPException(
                status_code=400,
                detail="Failed to generate try-on. Try again."
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
