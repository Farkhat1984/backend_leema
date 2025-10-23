"""
Wardrobe service - Business logic for user's personal clothing collection
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from app.models.wardrobe import UserWardrobeItem, WardrobeItemSource
from app.models.product import Product
from app.models.generation import Generation
from app.models.user import User
from app.schemas.wardrobe import (
    WardrobeItemCreate,
    WardrobeItemUpdate,
    WardrobeItemFromShop,
    WardrobeItemFromGeneration
)
from app.core.file_upload import UploadPath
from app.core.datetime_utils import utc_now
from typing import Optional, List, Tuple
from fastapi import UploadFile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WardrobeService:
    """Wardrobe service for managing user's personal clothing collection"""
    
    # Configuration
    MAX_WARDROBE_ITEMS_PER_USER = 500
    MAX_IMAGES_PER_ITEM = 5
    
    @staticmethod
    async def get_by_id(db: AsyncSession, wardrobe_id: int) -> Optional[UserWardrobeItem]:
        """Get wardrobe item by ID"""
        result = await db.execute(
            select(UserWardrobeItem).where(UserWardrobeItem.id == wardrobe_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def check_ownership(db: AsyncSession, wardrobe_id: int, user_id: int) -> bool:
        """Check if user owns the wardrobe item"""
        item = await WardrobeService.get_by_id(db, wardrobe_id)
        return item is not None and item.user_id == user_id
    
    @staticmethod
    async def get_user_wardrobe_count(db: AsyncSession, user_id: int) -> int:
        """Get total count of user's wardrobe items"""
        result = await db.execute(
            select(func.count(UserWardrobeItem.id)).where(
                UserWardrobeItem.user_id == user_id
            )
        )
        return result.scalar() or 0
    
    @staticmethod
    async def check_wardrobe_limit(db: AsyncSession, user_id: int) -> Tuple[bool, int]:
        """
        Check if user has reached wardrobe limit
        
        Returns:
            Tuple of (can_add: bool, current_count: int)
        """
        count = await WardrobeService.get_user_wardrobe_count(db, user_id)
        can_add = count < WardrobeService.MAX_WARDROBE_ITEMS_PER_USER
        return can_add, count
    
    @staticmethod
    async def get_user_wardrobe(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        source: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        folder: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[UserWardrobeItem], int]:
        """
        Get user's wardrobe items with filters and pagination
        
        Args:
            db: Database session
            user_id: User ID
            skip: Pagination offset
            limit: Items per page (max 100)
            source: Filter by source (shop_product, generated, uploaded, purchased)
            is_favorite: Filter by favorite status
            folder: Filter by folder name
            search: Search in name and description
            
        Returns:
            Tuple of (items, total_count)
        """
        # Limit max page size
        limit = min(limit, 100)
        
        # Build query
        query = select(UserWardrobeItem).where(UserWardrobeItem.user_id == user_id)
        
        # Apply filters
        if source:
            try:
                source_enum = WardrobeItemSource(source)
                query = query.where(UserWardrobeItem.source == source_enum)
            except ValueError:
                logger.warning(f"Invalid source filter: {source}")
        
        if is_favorite is not None:
            query = query.where(UserWardrobeItem.is_favorite == is_favorite)
        
        if folder:
            query = query.where(UserWardrobeItem.folder == folder)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    UserWardrobeItem.name.ilike(search_pattern),
                    UserWardrobeItem.description.ilike(search_pattern)
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting and pagination
        query = query.order_by(UserWardrobeItem.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()
        
        return items, total
    
    @staticmethod
    async def create_from_upload(
        db: AsyncSession,
        user_id: int,
        wardrobe_data: WardrobeItemCreate,
        files: Optional[List[UploadFile]] = None
    ) -> Optional[UserWardrobeItem]:
        """
        Create wardrobe item from user upload
        
        Args:
            db: Database session
            user_id: User ID
            wardrobe_data: Item data
            files: Uploaded image files
            
        Returns:
            Created wardrobe item or None if limit reached
        """
        # Check wardrobe limit
        can_add, count = await WardrobeService.check_wardrobe_limit(db, user_id)
        if not can_add:
            logger.warning(f"User {user_id} reached wardrobe limit ({count}/{WardrobeService.MAX_WARDROBE_ITEMS_PER_USER})")
            return None
        
        # Validate image count
        if files and len(files) > WardrobeService.MAX_IMAGES_PER_ITEM:
            logger.warning(f"Too many images: {len(files)} (max {WardrobeService.MAX_IMAGES_PER_ITEM})")
            return None
        
        # Create wardrobe item (without images first to get ID)
        wardrobe_item = UserWardrobeItem(
            user_id=user_id,
            source=WardrobeItemSource.UPLOADED,
            name=wardrobe_data.name,
            description=wardrobe_data.description,
            characteristics=wardrobe_data.characteristics,
            images=[],  # Will be filled after saving files
            is_favorite=wardrobe_data.is_favorite,
            folder=wardrobe_data.folder,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        
        db.add(wardrobe_item)
        await db.flush()  # Get the ID
        
        # Save uploaded files
        image_urls = []
        if files:
            for index, file in enumerate(files):
                try:
                    # Get upload path
                    file_path, relative_url = UploadPath.user_wardrobe(
                        user_id, wardrobe_item.id, file.filename, index
                    )
                    
                    # Save file
                    content = await file.read()
                    with open(file_path, "wb") as f:
                        f.write(content)
                    
                    image_urls.append(relative_url)
                    logger.info(f"Saved wardrobe image: {relative_url}")
                    
                except Exception as e:
                    logger.error(f"Error saving file: {e}")
                    # Continue with other files
        
        # Update images
        wardrobe_item.images = image_urls
        
        await db.commit()
        await db.refresh(wardrobe_item)
        
        logger.info(f"Wardrobe item created from upload: {wardrobe_item.id} for user {user_id}")
        return wardrobe_item
    
    @staticmethod
    async def create_from_shop(
        db: AsyncSession,
        user_id: int,
        product_id: int,
        custom_data: Optional[WardrobeItemFromShop] = None,
        copy_files: bool = False
    ) -> Optional[UserWardrobeItem]:
        """
        Create wardrobe item by copying from shop product
        
        Args:
            db: Database session
            user_id: User ID
            product_id: Product ID to copy from
            custom_data: Optional custom name/folder
            copy_files: If True, copy image files. If False, link to original
            
        Returns:
            Created wardrobe item or None if limit reached or product not found
        """
        # Check wardrobe limit
        can_add, count = await WardrobeService.check_wardrobe_limit(db, user_id)
        if not can_add:
            logger.warning(f"User {user_id} reached wardrobe limit ({count}/{WardrobeService.MAX_WARDROBE_ITEMS_PER_USER})")
            return None
        
        # Get product
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        
        if not product:
            logger.warning(f"Product {product_id} not found")
            return None
        
        # Use custom name or product name
        name = custom_data.name if custom_data and custom_data.name else product.name
        description = custom_data.description if custom_data and custom_data.description else product.description
        folder = custom_data.folder if custom_data and custom_data.folder else None
        is_favorite = custom_data.is_favorite if custom_data else False
        
        # Create wardrobe item
        wardrobe_item = UserWardrobeItem(
            user_id=user_id,
            source=WardrobeItemSource.SHOP_PRODUCT,
            original_product_id=product_id,
            name=name,
            description=description,
            characteristics=product.characteristics,
            images=product.images or [],  # Link to original images
            is_favorite=is_favorite,
            folder=folder,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        
        db.add(wardrobe_item)
        await db.flush()  # Get the ID
        
        # Copy files if requested
        if copy_files and product.images:
            copied_urls = []
            for index, image_url in enumerate(product.images[:WardrobeService.MAX_IMAGES_PER_ITEM]):
                try:
                    # Get destination path
                    dest_path, relative_url = UploadPath.user_wardrobe(
                        user_id, wardrobe_item.id, "image.jpg", index
                    )
                    
                    # Copy file
                    if UploadPath.copy_file(image_url, dest_path):
                        copied_urls.append(relative_url)
                    else:
                        # If copy fails, keep original URL
                        copied_urls.append(image_url)
                        
                except Exception as e:
                    logger.error(f"Error copying file: {e}")
                    copied_urls.append(image_url)  # Fallback to original
            
            wardrobe_item.images = copied_urls
        
        await db.commit()
        await db.refresh(wardrobe_item)
        
        logger.info(f"Wardrobe item created from shop product {product_id}: {wardrobe_item.id} for user {user_id}")
        return wardrobe_item
    
    @staticmethod
    async def create_from_generation(
        db: AsyncSession,
        user_id: int,
        generation_id: int,
        custom_data: Optional[WardrobeItemFromGeneration] = None
    ) -> Optional[UserWardrobeItem]:
        """
        Create wardrobe item from AI generation
        
        Args:
            db: Database session
            user_id: User ID
            generation_id: Generation ID
            custom_data: Optional custom name/folder
            
        Returns:
            Created wardrobe item or None if limit reached or generation not found
        """
        # Check wardrobe limit
        can_add, count = await WardrobeService.check_wardrobe_limit(db, user_id)
        if not can_add:
            logger.warning(f"User {user_id} reached wardrobe limit ({count}/{WardrobeService.MAX_WARDROBE_ITEMS_PER_USER})")
            return None
        
        # Get generation
        result = await db.execute(
            select(Generation).where(
                and_(
                    Generation.id == generation_id,
                    Generation.user_id == user_id  # Ensure ownership
                )
            )
        )
        generation = result.scalar_one_or_none()
        
        if not generation:
            logger.warning(f"Generation {generation_id} not found or doesn't belong to user {user_id}")
            return None
        
        # Use custom name or default
        name = custom_data.name if custom_data and custom_data.name else f"AI Generated - {generation.type.value}"
        description = custom_data.description if custom_data and custom_data.description else "Created with AI"
        folder = custom_data.folder if custom_data and custom_data.folder else "AI Creations"
        is_favorite = custom_data.is_favorite if custom_data else False
        
        # Create wardrobe item
        wardrobe_item = UserWardrobeItem(
            user_id=user_id,
            source=WardrobeItemSource.GENERATED,
            generation_id=generation_id,
            original_product_id=generation.product_id,  # Link to product if try-on
            name=name,
            description=description,
            characteristics=None,
            images=[generation.image_url] if generation.image_url else [],
            is_favorite=is_favorite,
            folder=folder,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        
        db.add(wardrobe_item)
        await db.commit()
        await db.refresh(wardrobe_item)
        
        logger.info(f"Wardrobe item created from generation {generation_id}: {wardrobe_item.id} for user {user_id}")
        return wardrobe_item
    
    @staticmethod
    async def update(
        db: AsyncSession,
        wardrobe_id: int,
        update_data: WardrobeItemUpdate
    ) -> Optional[UserWardrobeItem]:
        """
        Update wardrobe item
        
        Args:
            db: Database session
            wardrobe_id: Wardrobe item ID
            update_data: Update data
            
        Returns:
            Updated wardrobe item or None if not found
        """
        item = await WardrobeService.get_by_id(db, wardrobe_id)
        if not item:
            return None
        
        # Update fields
        if update_data.name is not None:
            item.name = update_data.name
        if update_data.description is not None:
            item.description = update_data.description
        if update_data.characteristics is not None:
            item.characteristics = update_data.characteristics
        if update_data.images is not None:
            item.images = update_data.images[:WardrobeService.MAX_IMAGES_PER_ITEM]
        if update_data.is_favorite is not None:
            item.is_favorite = update_data.is_favorite
        if update_data.folder is not None:
            item.folder = update_data.folder
        
        item.updated_at = utc_now()
        
        await db.commit()
        await db.refresh(item)
        
        logger.info(f"Wardrobe item {wardrobe_id} updated")
        return item
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        wardrobe_id: int,
        delete_files: bool = True
    ) -> bool:
        """
        Delete wardrobe item
        
        Args:
            db: Database session
            wardrobe_id: Wardrobe item ID
            delete_files: If True, delete associated files
            
        Returns:
            True if deleted, False if not found
        """
        item = await WardrobeService.get_by_id(db, wardrobe_id)
        if not item:
            return False
        
        user_id = item.user_id
        
        # Delete from database
        await db.delete(item)
        await db.commit()
        
        # Delete files if requested (only for uploaded items with copied files)
        if delete_files and item.source == WardrobeItemSource.UPLOADED:
            UploadPath.delete_wardrobe_item_files(user_id, wardrobe_id)
        
        logger.info(f"Wardrobe item {wardrobe_id} deleted")
        return True
    
    @staticmethod
    async def get_folders(db: AsyncSession, user_id: int) -> List[str]:
        """
        Get list of unique folder names for user's wardrobe
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of folder names
        """
        result = await db.execute(
            select(UserWardrobeItem.folder)
            .where(
                and_(
                    UserWardrobeItem.user_id == user_id,
                    UserWardrobeItem.folder.isnot(None)
                )
            )
            .distinct()
            .order_by(UserWardrobeItem.folder)
        )
        folders = [row[0] for row in result.all()]
        return folders
    
    @staticmethod
    async def get_stats(db: AsyncSession, user_id: int) -> dict:
        """
        Get wardrobe statistics for user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with stats
        """
        # Total count
        total_result = await db.execute(
            select(func.count(UserWardrobeItem.id)).where(
                UserWardrobeItem.user_id == user_id
            )
        )
        total = total_result.scalar() or 0
        
        # Count by source
        source_result = await db.execute(
            select(
                UserWardrobeItem.source,
                func.count(UserWardrobeItem.id)
            )
            .where(UserWardrobeItem.user_id == user_id)
            .group_by(UserWardrobeItem.source)
        )
        by_source = {row[0].value: row[1] for row in source_result.all()}
        
        # Favorites count
        favorites_result = await db.execute(
            select(func.count(UserWardrobeItem.id)).where(
                and_(
                    UserWardrobeItem.user_id == user_id,
                    UserWardrobeItem.is_favorite == True
                )
            )
        )
        favorites = favorites_result.scalar() or 0
        
        # Folder count
        folders_result = await db.execute(
            select(func.count(func.distinct(UserWardrobeItem.folder))).where(
                and_(
                    UserWardrobeItem.user_id == user_id,
                    UserWardrobeItem.folder.isnot(None)
                )
            )
        )
        folder_count = folders_result.scalar() or 0
        
        return {
            "total": total,
            "by_source": by_source,
            "favorites": favorites,
            "folders": folder_count,
            "limit": WardrobeService.MAX_WARDROBE_ITEMS_PER_USER,
            "remaining": max(0, WardrobeService.MAX_WARDROBE_ITEMS_PER_USER - total)
        }


# Export singleton instance
wardrobe_service = WardrobeService()
