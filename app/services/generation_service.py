from sqlalchemy.ext.asyncio import AsyncSession
from app.models.generation import Generation, GenerationType
from app.services.product_service import product_service
from app.core.gemini import gemini_ai
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GenerationService:
    """Generation and try-on service"""

    @staticmethod
    async def generate_fashion(
        db: AsyncSession,
        user_id: int,
        prompt: str,
        user_image_url: Optional[str] = None,
        cost: float = 0.0
    ) -> Optional[Generation]:
        """Generate fashion for user (charging handled by caller)"""
        # Generate image using Gemini
        image_url = await gemini_ai.generate_fashion(prompt, user_image_url)
        if not image_url:
            logger.error(f"Failed to generate fashion for user {user_id}")
            return None

        # Create generation record
        generation = Generation(
            user_id=user_id,
            type=GenerationType.GENERATION,
            image_url=image_url,
            cost=cost,
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)
        logger.info(f"Fashion generated for user {user_id}, cost: {cost}")
        return generation

    @staticmethod
    async def try_on_product(
        db: AsyncSession,
        user_id: int,
        product_id: int,
        user_image_url: str,
        cost: float = 0.0,
        save_to_wardrobe: bool = False
    ) -> tuple[Optional[Generation], Optional[int]]:
        """
        Try on product for user (charging handled by caller)
        Returns (generation, wardrobe_item_id)
        """
        product = await product_service.get_by_id(db, product_id)
        if not product or not product.is_active:
            logger.warning(f"Product {product_id} not found or inactive")
            return None, None

        # Get product image
        product_image_url = product.images[0] if product.images else None
        if not product_image_url:
            logger.error(f"Product {product_id} has no images")
            return None, None

        # Generate try-on image using Gemini
        image_url = await gemini_ai.try_on_fashion(product_image_url, user_image_url)
        if not image_url:
            logger.error(f"Failed to generate try-on for user {user_id}")
            return None, None

        # Create generation record
        generation = Generation(
            user_id=user_id,
            product_id=product_id,
            type=GenerationType.TRY_ON,
            image_url=image_url,
            cost=cost,
        )
        db.add(generation)

        # Increment product try-ons
        await product_service.increment_try_ons(db, product_id)

        await db.commit()
        await db.refresh(generation)
        logger.info(f"Try-on generated for user {user_id}, product {product_id}, cost: {cost}")

        # Save to wardrobe if requested
        wardrobe_item_id = None
        if save_to_wardrobe:
            try:
                from app.services.wardrobe_service import wardrobe_service
                from app.schemas.wardrobe import WardrobeItemFromGeneration
                
                # Check wardrobe limit before creating
                can_add, current_count = await wardrobe_service.check_wardrobe_limit(db, user_id)
                if can_add:
                    custom_data = WardrobeItemFromGeneration(
                        name=f"Try-on: {product.name}",
                        is_favorite=False
                    )
                    wardrobe_item = await wardrobe_service.create_from_generation(
                        db, user_id, generation.id, custom_data
                    )
                    wardrobe_item_id = wardrobe_item.id
                    logger.info(f"Generation {generation.id} saved to wardrobe: {wardrobe_item_id}")
                else:
                    logger.warning(f"User {user_id} wardrobe limit reached ({current_count}/500), skipping save")
            except Exception as e:
                logger.error(f"Failed to save generation to wardrobe: {e}")
                # Don't fail the whole operation if wardrobe save fails

        return generation, wardrobe_item_id

    @staticmethod
    async def apply_clothing_to_model(
        db: AsyncSession,
        user_id: int,
        clothing_image_url: str,
        model_image_url: str,
        cost: float = 0.0
    ) -> Optional[Generation]:
        """Apply clothing from image to model image (charging handled by caller)"""
        # Generate try-on image using Gemini
        image_url = await gemini_ai.apply_clothing_to_model(clothing_image_url, model_image_url)
        if not image_url:
            logger.error(f"Failed to apply clothing for user {user_id}")
            return None

        # Create generation record
        generation = Generation(
            user_id=user_id,
            type=GenerationType.TRY_ON,
            image_url=image_url,
            cost=cost,
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)
        logger.info(f"Clothing applied for user {user_id}, cost: {cost}")
        return generation


generation_service = GenerationService()
