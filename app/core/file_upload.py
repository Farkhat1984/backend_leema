"""
File upload utilities for organizing uploads by entity type
"""
from pathlib import Path
from typing import Optional
import uuid
import shutil
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class UploadPath:
    """Helper class for generating organized upload paths"""
    
    @staticmethod
    def shop_product(shop_id: int, product_id: int, filename: str) -> tuple[Path, str]:
        """
        Get path for shop product image
        
        Args:
            shop_id: Shop ID
            product_id: Product ID
            filename: Original filename (used for extension)
            
        Returns:
            Tuple of (full_file_path, relative_url)
        """
        # Create directory structure
        relative_dir = Path("shops") / str(shop_id) / "products" / str(product_id)
        full_dir = Path(settings.UPLOAD_DIR) / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with original extension
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{ext}"
        
        full_path = full_dir / unique_filename
        relative_url = f"/uploads/{relative_dir}/{unique_filename}"
        
        return full_path, relative_url
    
    @staticmethod
    def user_wardrobe(user_id: int, wardrobe_id: int, filename: str, index: int = 0) -> tuple[Path, str]:
        """
        Get path for user wardrobe item image
        
        Args:
            user_id: User ID
            wardrobe_id: Wardrobe item ID
            filename: Original filename (used for extension)
            index: Image index (for multiple images)
            
        Returns:
            Tuple of (full_file_path, relative_url)
        """
        # Create directory structure
        relative_dir = Path("users") / str(user_id) / "wardrobe" / str(wardrobe_id)
        full_dir = Path(settings.UPLOAD_DIR) / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        # Use indexed filename for consistency
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        indexed_filename = f"image_{index}.{ext}"
        
        full_path = full_dir / indexed_filename
        relative_url = f"/uploads/{relative_dir}/{indexed_filename}"
        
        return full_path, relative_url
    
    @staticmethod
    def generation(user_id: int, generation_id: int, suffix: str = "result") -> tuple[Path, str]:
        """
        Get path for AI generation result image
        
        Args:
            user_id: User ID
            generation_id: Generation ID
            suffix: File suffix (e.g., "original", "result")
            
        Returns:
            Tuple of (full_file_path, relative_url)
        """
        # Create directory structure
        relative_dir = Path("generations") / str(user_id)
        full_dir = Path(settings.UPLOAD_DIR) / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{generation_id}_{suffix}.jpg"
        full_path = full_dir / filename
        relative_url = f"/uploads/{relative_dir}/{filename}"
        
        return full_path, relative_url
    
    @staticmethod
    def user_avatar(user_id: int, filename: str) -> tuple[Path, str]:
        """
        Get path for user avatar image
        
        Args:
            user_id: User ID
            filename: Original filename (used for extension)
            
        Returns:
            Tuple of (full_file_path, relative_url)
        """
        # Create directory structure
        relative_dir = Path("users") / str(user_id)
        full_dir = Path(settings.UPLOAD_DIR) / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        avatar_filename = f"avatar.{ext}"
        
        full_path = full_dir / avatar_filename
        relative_url = f"/uploads/{relative_dir}/{avatar_filename}"
        
        return full_path, relative_url
    
    @staticmethod
    def shop_avatar(shop_id: int, filename: str) -> tuple[Path, str]:
        """
        Get path for shop avatar/logo image
        
        Args:
            shop_id: Shop ID
            filename: Original filename (used for extension)
            
        Returns:
            Tuple of (full_file_path, relative_url)
        """
        # Create directory structure
        relative_dir = Path("shops") / str(shop_id)
        full_dir = Path(settings.UPLOAD_DIR) / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        avatar_filename = f"avatar.{ext}"
        
        full_path = full_dir / avatar_filename
        relative_url = f"/uploads/{relative_dir}/{avatar_filename}"
        
        return full_path, relative_url
    
    @staticmethod
    def temp_file(filename: str) -> tuple[Path, str]:
        """
        Get path for temporary file (cleaned up after 24h)
        
        Args:
            filename: Original filename
            
        Returns:
            Tuple of (full_file_path, relative_url)
        """
        relative_dir = Path("temp")
        full_dir = Path(settings.UPLOAD_DIR) / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{ext}"
        
        full_path = full_dir / unique_filename
        relative_url = f"/uploads/{relative_dir}/{unique_filename}"
        
        return full_path, relative_url
    
    @staticmethod
    def copy_file(source_path: str, dest_path: Path) -> bool:
        """
        Copy file from source to destination
        
        Args:
            source_path: Source file path (can be URL or local path)
            dest_path: Destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle local paths (starting with /uploads/ or uploads/)
            if source_path.startswith('/uploads/'):
                source_full = Path(settings.UPLOAD_DIR) / source_path[9:]  # Remove /uploads/
            elif source_path.startswith('uploads/'):
                source_full = Path(settings.UPLOAD_DIR) / source_path[8:]  # Remove uploads/
            elif source_path.startswith(settings.UPLOAD_DIR):
                source_full = Path(source_path)
            else:
                # If it's a full URL, extract the path
                if '/uploads/' in source_path:
                    path_part = source_path.split('/uploads/')[-1]
                    source_full = Path(settings.UPLOAD_DIR) / path_part
                else:
                    logger.error(f"Cannot parse source path: {source_path}")
                    return False
            
            if not source_full.exists():
                logger.error(f"Source file does not exist: {source_full}")
                return False
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_full, dest_path)
            logger.info(f"File copied: {source_full} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    @staticmethod
    def delete_directory(entity_type: str, entity_id: int) -> bool:
        """
        Delete entire directory for an entity
        
        Args:
            entity_type: Type of entity (user, shop, wardrobe, etc.)
            entity_id: Entity ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if entity_type == "wardrobe":
                # For wardrobe items, we need user_id and wardrobe_id
                # This is called differently - see delete_wardrobe_item_files
                logger.warning("Use delete_wardrobe_item_files for wardrobe items")
                return False
            
            entity_dir = Path(settings.UPLOAD_DIR) / entity_type / str(entity_id)
            if entity_dir.exists():
                shutil.rmtree(entity_dir)
                logger.info(f"Directory deleted: {entity_dir}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting directory: {e}")
            return False
    
    @staticmethod
    def delete_wardrobe_item_files(user_id: int, wardrobe_id: int) -> bool:
        """
        Delete all files for a wardrobe item
        
        Args:
            user_id: User ID
            wardrobe_id: Wardrobe item ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            wardrobe_dir = Path(settings.UPLOAD_DIR) / "users" / str(user_id) / "wardrobe" / str(wardrobe_id)
            if wardrobe_dir.exists():
                shutil.rmtree(wardrobe_dir)
                logger.info(f"Wardrobe item files deleted: {wardrobe_dir}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting wardrobe item files: {e}")
            return False
    
    @staticmethod
    def delete_generation_files(user_id: int, generation_id: int) -> bool:
        """
        Delete all files for a generation
        
        Args:
            user_id: User ID
            generation_id: Generation ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            gen_dir = Path(settings.UPLOAD_DIR) / "generations" / str(user_id)
            if gen_dir.exists():
                # Delete all files matching generation_id pattern
                deleted_count = 0
                for file_path in gen_dir.glob(f"{generation_id}_*.jpg"):
                    file_path.unlink()
                    logger.info(f"Generation file deleted: {file_path}")
                    deleted_count += 1
                return deleted_count > 0
            return False
        except Exception as e:
            logger.error(f"Error deleting generation files: {e}")
            return False
    
    @staticmethod
    def get_full_url(relative_url: str) -> str:
        """
        Convert relative URL to full URL
        
        Args:
            relative_url: Relative URL (e.g., /uploads/users/1/avatar.jpg)
            
        Returns:
            Full URL with domain/CDN prefix
        """
        # Use UPLOAD_URL_PREFIX if set (for CDN), otherwise use API domain
        base_url = settings.UPLOAD_URL_PREFIX if settings.UPLOAD_URL_PREFIX else ""
        
        # If no base URL, return relative (will be resolved by client)
        if not base_url:
            return relative_url
        
        # Remove trailing slash from base_url
        base_url = base_url.rstrip('/')
        
        # Ensure relative_url starts with /
        if not relative_url.startswith('/'):
            relative_url = '/' + relative_url
        
        return f"{base_url}{relative_url}"
