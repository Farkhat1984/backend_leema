import google.genai as genai
from google.genai import types
from app.config import settings
from typing import Optional
import logging
import os
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


class GeminiAI:
    """Google Gemini AI handler for fashion generation"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Ensure upload directory exists
        self.upload_dir = Path(settings.UPLOAD_DIR) / "generations"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _save_image(self, image_data: bytes) -> str:
        """Save image bytes to disk and return URL path"""
        try:
            # Generate unique filename
            filename = f"{uuid.uuid4()}.png"
            filepath = self.upload_dir / filename

            # Save image
            image = Image.open(BytesIO(image_data))
            image.save(filepath, "PNG")

            # Return relative URL path
            return f"/uploads/generations/{filename}"
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None

    async def generate_fashion(self, prompt: str, user_image_url: Optional[str] = None) -> Optional[str]:
        """
        Generate fashion image based on prompt
        Returns: Generated image URL or None
        """
        try:
            system_instruction = (
                "You are an AI photographer specializing in professional fashion photography. "
                "Generate ONLY images, never text. Create photorealistic, high-quality full-body portraits. "
                "Use studio lighting, maintain sharp focus, and ensure professional composition."
            )

            user_prompt = (
                f'Create a photorealistic full-body portrait of a model in a vertical 2:3 composition. '
                f'The model should be: {prompt}. '
                f'Use professional studio lighting with soft shadows, neutral background, '
                f'and ensure the model is centered in the frame. The image must be in portrait orientation.'
            )

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio="2:3",
                    )
                )
            )

            # Extract image from response
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Generated fashion image: {image_url}")
                            return image_url

            logger.error("No image found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return None

    async def try_on_fashion(self, product_image_url: str, user_image_url: str) -> Optional[str]:
        """
        Try on fashion item on user image
        Returns: Generated try-on image URL or None
        """
        try:
            system_instruction = (
                "You are a professional AI fashion photographer and virtual stylist. "
                "Generate ONLY photorealistic images, never text. "
                "Your specialty is creating seamless, natural-looking virtual clothing try-ons while preserving the person's identity perfectly."
            )

            user_prompt = (
                'This is a professional e-commerce fashion photoshoot. '
                'Take the clothing item from the second image and dress the person from the first image in it. '
                'The result should look like a natural studio photograph where the person is actually wearing this exact clothing. '
                'The person\'s face, hair, eyes, skin tone, and body proportions remain completely unchanged - they are the same person. '
                'The clothing fits naturally on their body with realistic fabric texture, wrinkles, and shadows that match the studio lighting. '
                'The background, pose, and camera angle stay identical to the original portrait.'
            )

            # Load images from disk
            person_image = self._load_image(user_image_url)
            product_image = self._load_image(product_image_url)

            if not person_image or not product_image:
                logger.error("Failed to load images for try-on")
                return None

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[person_image, product_image, user_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio="2:3",
                    )
                )
            )

            # Extract image from response
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Generated try-on image: {image_url}")
                            return image_url

            logger.error("No image found in Gemini try-on response")
            return None

        except Exception as e:
            logger.error(f"Gemini try-on error: {e}")
            return None

    async def apply_clothing_to_model(self, clothing_image_url: str, model_image_url: str) -> Optional[str]:
        """
        Apply clothing from one image onto a model in another image
        Returns: Generated image URL or None
        """
        # Same as try_on_fashion but with model first
        return await self.try_on_fashion(model_image_url, clothing_image_url)

    def _load_image(self, image_path: str):
        """Load image from local path"""
        try:
            # If it's a relative path, convert to absolute
            if image_path.startswith('/uploads/'):
                image_path = '.' + image_path

            if os.path.exists(image_path):
                # Load and return PIL Image object
                return Image.open(image_path)
            else:
                logger.error(f"Image not found: {image_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return None


gemini_ai = GeminiAI()
