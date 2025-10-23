"""
Wardrobe API - User's personal clothing collection endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.wardrobe import UserWardrobeItem
from app.services.wardrobe_service import wardrobe_service
from app.schemas.wardrobe import (
    WardrobeItemCreate,
    WardrobeItemResponse,
    WardrobeItemUpdate,
    WardrobeItemFromShop,
    WardrobeItemFromGeneration,
    WardrobeListResponse,
    WardrobeItemDeleted,
    WardrobeItemSourceEnum
)
from app.core.file_upload import UploadPath
from app.config import settings
from typing import List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=WardrobeListResponse)
async def get_wardrobe(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    source: Optional[str] = Query(None, description="Filter by source: shop_product, generated, uploaded, purchased"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    folder: Optional[str] = Query(None, description="Filter by folder name"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's wardrobe items with filters and pagination
    
    - **skip**: Pagination offset (default: 0)
    - **limit**: Items per page, max 100 (default: 50)
    - **source**: Filter by source type
    - **is_favorite**: Filter favorites only
    - **folder**: Filter by folder/collection
    - **search**: Search in name and description
    """
    # Validate source enum if provided
    if source:
        try:
            WardrobeItemSourceEnum(source)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {[s.value for s in WardrobeItemSourceEnum]}"
            )
    
    items, total = await wardrobe_service.get_user_wardrobe(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        source=source,
        is_favorite=is_favorite,
        folder=folder,
        search=search
    )
    
    page = skip // limit + 1
    has_more = (skip + limit) < total
    
    return WardrobeListResponse(
        items=[WardrobeItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=limit,
        has_more=has_more
    )


@router.get("/stats")
async def get_wardrobe_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get wardrobe statistics for current user
    
    Returns:
    - total: Total number of items
    - by_source: Count by each source type
    - favorites: Number of favorite items
    - folders: Number of unique folders
    - limit: Maximum items allowed
    - remaining: Remaining slots
    """
    stats = await wardrobe_service.get_stats(db, current_user.id)
    return stats


@router.get("/folders")
async def get_wardrobe_folders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of unique folder names in user's wardrobe
    
    Returns array of folder names sorted alphabetically
    """
    folders = await wardrobe_service.get_folders(db, current_user.id)
    return {"folders": folders}


@router.get("/{wardrobe_id}", response_model=WardrobeItemResponse)
async def get_wardrobe_item(
    wardrobe_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get single wardrobe item by ID
    
    Only returns items owned by current user
    """
    # Check ownership
    is_owner = await wardrobe_service.check_ownership(db, wardrobe_id, current_user.id)
    if not is_owner:
        raise HTTPException(
            status_code=404,
            detail="Wardrobe item not found"
        )
    
    item = await wardrobe_service.get_by_id(db, wardrobe_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    
    return WardrobeItemResponse.model_validate(item)


@router.post("/upload-images")
async def upload_wardrobe_images(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload images for wardrobe items (returns URLs only, doesn't create item)
    
    - Max 5 images per upload
    - Allowed formats: jpg, jpeg, png, webp
    - Max size per file: 10MB
    
    Use these URLs when creating a wardrobe item
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 5:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum 5 images allowed, got {len(files)}"
        )
    
    # Validate file types
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: jpeg, jpg, png, webp"
            )
    
    # Validate file sizes
    saved_urls = []
    for file in files:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} too large. Max size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
            )
        
        # Save to temp directory (will be moved when item is created)
        file_path, relative_url = UploadPath.temp_file(file.filename)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Get full URL
        full_url = UploadPath.get_full_url(relative_url)
        saved_urls.append(full_url)
        logger.info(f"Uploaded temp wardrobe image: {relative_url}")
    
    return {"urls": saved_urls}


@router.post("/", response_model=WardrobeItemResponse)
async def create_wardrobe_item(
    name: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None),
    characteristics: Optional[str] = Form(None),
    image_urls: Optional[str] = Form(None),
    is_favorite: bool = Form(False),
    folder: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new wardrobe item by uploading images and data
    
    Can provide either:
    - files: Upload new images directly
    - image_urls: Use URLs from /upload-images endpoint (JSON array as string)
    
    **Form fields:**
    - name: Item name (required)
    - description: Item description (optional)
    - characteristics: JSON string of characteristics (optional)
    - image_urls: JSON array of image URLs (optional)
    - is_favorite: Mark as favorite (default: false)
    - folder: Folder/collection name (optional)
    - files: Image files to upload (optional, max 5)
    """
    # Check wardrobe limit
    can_add, count = await wardrobe_service.check_wardrobe_limit(db, current_user.id)
    if not can_add:
        raise HTTPException(
            status_code=403,
            detail=f"Wardrobe limit reached ({count}/{wardrobe_service.MAX_WARDROBE_ITEMS_PER_USER}). Delete some items to add more."
        )
    
    # Parse characteristics
    chars = None
    if characteristics:
        try:
            chars = json.loads(characteristics)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid characteristics format. Must be valid JSON."
            )
    
    # Parse image URLs
    images = []
    if image_urls:
        try:
            images = json.loads(image_urls)
            if not isinstance(images, list):
                raise HTTPException(
                    status_code=400,
                    detail="image_urls must be a JSON array"
                )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid image_urls format. Must be valid JSON array."
            )
    
    # Create wardrobe data
    wardrobe_data = WardrobeItemCreate(
        name=name,
        description=description,
        characteristics=chars,
        is_favorite=is_favorite,
        folder=folder,
        images=images if images else None
    )
    
    # Create item with files
    wardrobe_item = await wardrobe_service.create_from_upload(
        db=db,
        user_id=current_user.id,
        wardrobe_data=wardrobe_data,
        files=files
    )
    
    if not wardrobe_item:
        raise HTTPException(
            status_code=500,
            detail="Failed to create wardrobe item"
        )
    
    logger.info(f"Wardrobe item created: {wardrobe_item.id} for user {current_user.id}")
    return WardrobeItemResponse.model_validate(wardrobe_item)


@router.post("/from-shop/{product_id}", response_model=WardrobeItemResponse)
async def add_from_shop(
    product_id: int,
    custom_data: Optional[WardrobeItemFromShop] = None,
    copy_files: bool = Query(False, description="Copy image files (true) or link to original (false)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add product from shop to wardrobe
    
    Creates a copy of the product in user's wardrobe that can be edited.
    
    **Path parameters:**
    - product_id: ID of the shop product to copy
    
    **Query parameters:**
    - copy_files: If true, copies image files. If false, links to originals (default: false)
    
    **Body (optional):**
    - name: Custom name (overrides product name)
    - description: Custom description
    - folder: Folder to add item to
    - is_favorite: Mark as favorite
    """
    # Check wardrobe limit
    can_add, count = await wardrobe_service.check_wardrobe_limit(db, current_user.id)
    if not can_add:
        raise HTTPException(
            status_code=403,
            detail=f"Wardrobe limit reached ({count}/{wardrobe_service.MAX_WARDROBE_ITEMS_PER_USER})"
        )
    
    # Create wardrobe item from shop product
    wardrobe_item = await wardrobe_service.create_from_shop(
        db=db,
        user_id=current_user.id,
        product_id=product_id,
        custom_data=custom_data,
        copy_files=copy_files
    )
    
    if not wardrobe_item:
        raise HTTPException(
            status_code=404,
            detail="Product not found or failed to add to wardrobe"
        )
    
    logger.info(f"Product {product_id} added to wardrobe: {wardrobe_item.id} for user {current_user.id}")
    return WardrobeItemResponse.model_validate(wardrobe_item)


@router.post("/from-generation/{generation_id}", response_model=WardrobeItemResponse)
async def save_generation(
    generation_id: int,
    custom_data: Optional[WardrobeItemFromGeneration] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save AI generation to wardrobe
    
    **Path parameters:**
    - generation_id: ID of the generation to save
    
    **Body (optional):**
    - name: Custom name (default: "AI Generated - {type}")
    - description: Custom description (default: "Created with AI")
    - folder: Folder to add item to (default: "AI Creations")
    - is_favorite: Mark as favorite
    """
    # Check wardrobe limit
    can_add, count = await wardrobe_service.check_wardrobe_limit(db, current_user.id)
    if not can_add:
        raise HTTPException(
            status_code=403,
            detail=f"Wardrobe limit reached ({count}/{wardrobe_service.MAX_WARDROBE_ITEMS_PER_USER})"
        )
    
    # Create wardrobe item from generation
    wardrobe_item = await wardrobe_service.create_from_generation(
        db=db,
        user_id=current_user.id,
        generation_id=generation_id,
        custom_data=custom_data
    )
    
    if not wardrobe_item:
        raise HTTPException(
            status_code=404,
            detail="Generation not found or doesn't belong to you"
        )
    
    logger.info(f"Generation {generation_id} saved to wardrobe: {wardrobe_item.id} for user {current_user.id}")
    return WardrobeItemResponse.model_validate(wardrobe_item)


@router.put("/{wardrobe_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    wardrobe_id: int,
    update_data: WardrobeItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update wardrobe item
    
    Can update: name, description, characteristics, images, is_favorite, folder
    
    All fields are optional - only provided fields will be updated
    """
    # Check ownership
    is_owner = await wardrobe_service.check_ownership(db, wardrobe_id, current_user.id)
    if not is_owner:
        raise HTTPException(
            status_code=404,
            detail="Wardrobe item not found"
        )
    
    # Update item
    updated_item = await wardrobe_service.update(db, wardrobe_id, update_data)
    if not updated_item:
        raise HTTPException(
            status_code=404,
            detail="Wardrobe item not found"
        )
    
    logger.info(f"Wardrobe item {wardrobe_id} updated by user {current_user.id}")
    return WardrobeItemResponse.model_validate(updated_item)


@router.delete("/{wardrobe_id}", response_model=WardrobeItemDeleted)
async def delete_wardrobe_item(
    wardrobe_id: int,
    delete_files: bool = Query(True, description="Delete associated image files"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete wardrobe item
    
    **Path parameters:**
    - wardrobe_id: ID of the wardrobe item to delete
    
    **Query parameters:**
    - delete_files: If true, deletes image files (default: true). Only affects uploaded items.
    """
    # Check ownership
    is_owner = await wardrobe_service.check_ownership(db, wardrobe_id, current_user.id)
    if not is_owner:
        raise HTTPException(
            status_code=404,
            detail="Wardrobe item not found"
        )
    
    # Delete item
    deleted = await wardrobe_service.delete(db, wardrobe_id, delete_files=delete_files)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Wardrobe item not found"
        )
    
    logger.info(f"Wardrobe item {wardrobe_id} deleted by user {current_user.id}")
    return WardrobeItemDeleted(
        message="Wardrobe item deleted successfully",
        id=wardrobe_id
    )
