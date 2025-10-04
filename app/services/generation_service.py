from sqlalchemy.ext.asyncio import AsyncSession
from app.models.generation import Generation, GenerationType
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.user import User
from app.services.user_service import user_service
from app.services.product_service import product_service
from app.services.settings_service import settings_service
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
        user_image_url: Optional[str] = None
    ) -> Optional[Generation]:
        """Generate fashion for user"""
        user = await user_service.get_by_id(db, user_id)
        if not user:
            return None

        # Get price
        price = await settings_service.get_setting_float(db, "user_generation_price", 1.0)

        # Check if user has free generations
        if user.free_generations_left > 0:
            cost = 0.0
            user.free_generations_left -= 1
        else:
            # Check balance
            if float(user.balance) < price:
                logger.warning(f"User {user_id} has insufficient balance for generation")
                return None
            cost = price
            user.balance = float(user.balance) - cost

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

        # Create transaction if cost > 0
        if cost > 0:
            transaction = Transaction(
                user_id=user_id,
                type=TransactionType.GENERATION,
                amount=cost,
                status=TransactionStatus.COMPLETED,
                extra_data={"generation_id": generation.id, "prompt": prompt}
            )
            db.add(transaction)

        await db.commit()
        await db.refresh(generation)
        logger.info(f"Fashion generated for user {user_id}, cost: {cost}")
        return generation

    @staticmethod
    async def try_on_product(
        db: AsyncSession,
        user_id: int,
        product_id: int,
        user_image_url: str
    ) -> Optional[Generation]:
        """Try on product for user"""
        user = await user_service.get_by_id(db, user_id)
        if not user:
            return None

        product = await product_service.get_by_id(db, product_id)
        if not product or not product.is_active:
            return None

        # Get price
        price = await settings_service.get_setting_float(db, "user_try_on_price", 0.5)

        # Check if user has free try-ons
        if user.free_try_ons_left > 0:
            cost = 0.0
            user.free_try_ons_left -= 1
        else:
            # Check balance
            if float(user.balance) < price:
                logger.warning(f"User {user_id} has insufficient balance for try-on")
                return None
            cost = price
            user.balance = float(user.balance) - cost

        # Get product image
        product_image_url = product.images[0] if product.images else None
        if not product_image_url:
            logger.error(f"Product {product_id} has no images")
            return None

        # Generate try-on image using Gemini
        image_url = await gemini_ai.try_on_fashion(product_image_url, user_image_url)
        if not image_url:
            logger.error(f"Failed to generate try-on for user {user_id}")
            return None

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

        # Create transaction if cost > 0
        if cost > 0:
            transaction = Transaction(
                user_id=user_id,
                type=TransactionType.TRY_ON,
                amount=cost,
                status=TransactionStatus.COMPLETED,
                extra_data={"generation_id": generation.id, "product_id": product_id}
            )
            db.add(transaction)

        await db.commit()
        await db.refresh(generation)
        logger.info(f"Try-on generated for user {user_id}, product {product_id}, cost: {cost}")
        return generation

    @staticmethod
    async def apply_clothing_to_model(
        db: AsyncSession,
        user_id: int,
        clothing_image_url: str,
        model_image_url: str
    ) -> Optional[Generation]:
        """Apply clothing from image to model image"""
        user = await user_service.get_by_id(db, user_id)
        if not user:
            return None

        # Get price (use try-on price as it's similar operation)
        price = await settings_service.get_setting_float(db, "user_try_on_price", 0.5)

        # Check if user has free try-ons
        if user.free_try_ons_left > 0:
            cost = 0.0
            user.free_try_ons_left -= 1
        else:
            # Check balance
            if float(user.balance) < price:
                logger.warning(f"User {user_id} has insufficient balance for apply clothing")
                return None
            cost = price
            user.balance = float(user.balance) - cost

        # Generate try-on image using Gemini
        image_url = await gemini_ai.apply_clothing_to_model(clothing_image_url, model_image_url)
        if not image_url:
            logger.error(f"Failed to apply clothing for user {user_id}")
            return None

        # Create generation record
        generation = Generation(
            user_id=user_id,
            type=GenerationType.TRY_ON,  # Using TRY_ON type as it's similar
            image_url=image_url,
            cost=cost,
        )
        db.add(generation)

        # Create transaction if cost > 0
        if cost > 0:
            transaction = Transaction(
                user_id=user_id,
                type=TransactionType.TRY_ON,
                amount=cost,
                status=TransactionStatus.COMPLETED,
                extra_data={
                    "generation_id": generation.id,
                    "clothing_image_url": clothing_image_url,
                    "model_image_url": model_image_url
                }
            )
            db.add(transaction)

        await db.commit()
        await db.refresh(generation)
        logger.info(f"Clothing applied for user {user_id}, cost: {cost}")
        return generation


generation_service = GenerationService()
