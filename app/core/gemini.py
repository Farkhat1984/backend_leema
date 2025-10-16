import google.genai as genai
from google.genai import types
from app.config import settings
from typing import Optional, List
import logging
import os
import uuid
import base64
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

    def _base64_to_image(self, base64_string: str) -> Optional[Image.Image]:
        """Convert base64 string to PIL Image"""
        try:
            # Remove data URI prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',', 1)[1]

            image_data = base64.b64decode(base64_string)
            return Image.open(BytesIO(image_data))
        except Exception as e:
            logger.error(f"Error converting base64 to image: {e}")
            return None

    async def generate_person(self, description: str, aspect_ratio: str = "2:3") -> Optional[str]:
        """
        Generate a person/model image from description
        Returns: Generated image URL or None
        """
        try:
            system_instruction = (
                "You are a professional AI photographer specializing in portrait photography. "
                "Generate ONLY photorealistic images of people, never text or illustrations. "
                "Focus on creating natural, professional-quality portraits with proper lighting, "
                "realistic skin tones, natural expressions, and professional composition."
            )

            user_prompt = (
                f'Create a photorealistic portrait photograph of a person. '
                f'Description: {description}. '
                f'Use professional studio lighting, maintain sharp focus on the face, '
                f'natural background, and ensure the person looks natural and professional. '
                f'The image should look like a real photograph taken by a professional photographer.'
            )

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )

            # Extract and save image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Generated person image: {image_url}")
                            return image_url

            logger.error("No image found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini person generation error: {e}")
            return None

    async def generate_clothing(self, description: str, aspect_ratio: str = "1:1") -> Optional[str]:
        """
        Generate clothing image from description
        Returns: Generated image URL or None
        """
        try:
            system_instruction = (
                "You are a professional product photographer specializing in fashion and clothing. "
                "Generate ONLY photorealistic images of clothing items, never text. "
                "Create clean, professional product photos with proper lighting, sharp details, "
                "and neutral backgrounds suitable for e-commerce."
            )

            user_prompt = (
                f'Create a professional product photograph of clothing. '
                f'Description: {description}. '
                f'Use clean white or neutral background, professional studio lighting, '
                f'show the clothing item clearly with all details visible. '
                f'The image should look like a high-quality e-commerce product photo.'
            )

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )

            # Extract and save image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Generated clothing image: {image_url}")
                            return image_url

            logger.error("No image found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini clothing generation error: {e}")
            return None

    async def apply_clothing_base64(
        self,
        person_base64: str,
        clothing_base64: Optional[str] = None,
        description: Optional[str] = None,
        aspect_ratio: str = "2:3"
    ) -> Optional[str]:
        """
        Apply clothing to model using base64 encoded images
        Either provide clothing_base64 OR description
        Returns: Generated image URL or None
        """
        try:
            # Convert base64 to PIL Image
            person_image = self._base64_to_image(person_base64)
            if not person_image:
                logger.error("Failed to decode person base64 image")
                return None

            system_instruction = (
                "You are a professional AI fashion photographer and virtual stylist. "
                "Generate ONLY photorealistic images, never text. "
                "Create seamless virtual try-ons that look completely natural and professional."
            )

            contents = [person_image]

            if clothing_base64:
                # Using clothing image
                clothing_image = self._base64_to_image(clothing_base64)
                if not clothing_image:
                    logger.error("Failed to decode clothing base64 image")
                    return None

                contents.append(clothing_image)
                user_prompt = (
                    'Take the clothing from the second image and naturally dress the person from the first image in it. '
                    'The result should look like a professional photograph where the person is actually wearing this clothing. '
                    'Preserve the person\'s identity, facial features, and body proportions completely. '
                    'Make the clothing fit naturally with realistic fabric texture, wrinkles, and lighting.'
                )
            elif description:
                # Using text description
                user_prompt = (
                    f'Dress the person in this image in the following clothing: {description}. '
                    f'The result should look like a professional photograph. '
                    f'Preserve the person\'s identity, facial features, and body proportions completely. '
                    f'Make the clothing fit naturally with realistic fabric texture, wrinkles, and lighting.'
                )
            else:
                logger.error("Must provide either clothing_base64 or description")
                return None

            contents.append(user_prompt)

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )

            # Extract and save image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Applied clothing to model: {image_url}")
                            return image_url

            logger.error("No image found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini apply clothing error: {e}")
            return None

    async def generate_image_from_text(
        self,
        prompt: str,
        aspect_ratio: str = "1:1"
    ) -> Optional[str]:
        """
        Generate image from text prompt using Gemini 2.5 Flash Image
        Returns: Generated image URL or None
        """
        try:
            system_instruction = (
                "You are a professional AI image generator. "
                "Generate ONLY high-quality photorealistic images, never text. "
                "Create detailed, visually appealing images that match the user's description perfectly."
            )

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )

            # Extract and save image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Generated image from text: {image_url}")
                            return image_url

            logger.error("No image found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini text to image error: {e}")
            return None

    async def generate_image_from_text_and_images(
        self,
        prompt: str,
        images_base64: List[str],
        aspect_ratio: str = "1:1"
    ) -> Optional[str]:
        """
        Generate image from text and reference images
        Returns: Generated image URL or None
        """
        try:
            # Convert all base64 images to PIL Images
            reference_images = []
            for idx, img_base64 in enumerate(images_base64):
                image = self._base64_to_image(img_base64)
                if not image:
                    logger.error(f"Failed to decode image {idx + 1}")
                    continue
                reference_images.append(image)

            if not reference_images:
                logger.error("No valid reference images provided")
                return None

            system_instruction = (
                "You are a professional AI image generator. "
                "Generate ONLY high-quality photorealistic images, never text. "
                "Use the provided reference images as inspiration and guidance, "
                "and create a new image that matches the user's text description."
            )

            # Build contents: reference images + prompt
            contents = reference_images + [prompt]

            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['Image'],
                    system_instruction=system_instruction,
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )

            # Extract and save image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_url = self._save_image(part.inline_data.data)
                        if image_url:
                            logger.info(f"Generated image from text and images: {image_url}")
                            return image_url

            logger.error("No image found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini text+images to image error: {e}")
            return None


gemini_ai = GeminiAI()
