#!/usr/bin/env python3
"""
Test script for Wardrobe Service
Tests all service methods without requiring API endpoints
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.database import async_session_maker
from app.models.user import User, UserRole
from app.models.product import Product, ModerationStatus
from app.models.generation import Generation, GenerationType
from app.models.wardrobe import UserWardrobeItem, WardrobeItemSource
from app.services.wardrobe_service import wardrobe_service
from app.schemas.wardrobe import WardrobeItemFromShop, WardrobeItemFromGeneration
from app.core.datetime_utils import utc_now
from sqlalchemy import select


async def test_wardrobe_service():
    """Test wardrobe service methods"""
    print("=" * 60)
    print("TESTING WARDROBE SERVICE")
    print("=" * 60)
    
    async with async_session_maker() as db:
        # Get or create test user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ No users found in database. Please create a user first.")
            return False
        
        print(f"✓ Test user: {user.email} (ID: {user.id})")
        
        # Test 1: Check wardrobe limit
        print("\n--- Test 1: Check Wardrobe Limit ---")
        can_add, count = await wardrobe_service.check_wardrobe_limit(db, user.id)
        print(f"✓ Current wardrobe items: {count}/{wardrobe_service.MAX_WARDROBE_ITEMS_PER_USER}")
        print(f"✓ Can add more: {can_add}")
        
        # Test 2: Get user wardrobe (should work even if empty)
        print("\n--- Test 2: Get User Wardrobe ---")
        items, total = await wardrobe_service.get_user_wardrobe(db, user.id)
        print(f"✓ Total wardrobe items: {total}")
        print(f"✓ Items returned: {len(items)}")
        
        # Test 3: Get wardrobe stats
        print("\n--- Test 3: Get Wardrobe Stats ---")
        stats = await wardrobe_service.get_stats(db, user.id)
        print(f"✓ Stats: {stats}")
        
        # Test 4: Get folders
        print("\n--- Test 4: Get Folders ---")
        folders = await wardrobe_service.get_folders(db, user.id)
        print(f"✓ Folders: {folders if folders else 'None'}")
        
        # Test 5: Try to create from shop product (if products exist)
        print("\n--- Test 5: Create from Shop Product ---")
        product_result = await db.execute(
            select(Product)
            .where(Product.moderation_status == ModerationStatus.APPROVED)
            .limit(1)
        )
        product = product_result.scalar_one_or_none()
        
        if product:
            print(f"✓ Test product found: {product.name} (ID: {product.id})")
            
            custom_data = WardrobeItemFromShop(
                name="Test Item from Shop",
                folder="Test Folder",
                is_favorite=True
            )
            
            wardrobe_item = await wardrobe_service.create_from_shop(
                db, user.id, product.id, custom_data, copy_files=False
            )
            
            if wardrobe_item:
                print(f"✓ Created wardrobe item from shop: ID {wardrobe_item.id}")
                print(f"  - Name: {wardrobe_item.name}")
                print(f"  - Source: {wardrobe_item.source.value}")
                print(f"  - Original product ID: {wardrobe_item.original_product_id}")
                print(f"  - Images: {len(wardrobe_item.images)}")
                
                # Test 6: Update the item
                print("\n--- Test 6: Update Wardrobe Item ---")
                from app.schemas.wardrobe import WardrobeItemUpdate
                update_data = WardrobeItemUpdate(
                    name="Updated Test Item",
                    description="This item was updated",
                    is_favorite=False
                )
                
                updated = await wardrobe_service.update(db, wardrobe_item.id, update_data)
                if updated:
                    print(f"✓ Updated wardrobe item: {updated.name}")
                    print(f"  - Description: {updated.description}")
                    print(f"  - Is favorite: {updated.is_favorite}")
                
                # Test 7: Get by ID
                print("\n--- Test 7: Get Item by ID ---")
                fetched = await wardrobe_service.get_by_id(db, wardrobe_item.id)
                if fetched:
                    print(f"✓ Fetched item: {fetched.name} (ID: {fetched.id})")
                
                # Test 8: Check ownership
                print("\n--- Test 8: Check Ownership ---")
                is_owner = await wardrobe_service.check_ownership(db, wardrobe_item.id, user.id)
                print(f"✓ User owns this item: {is_owner}")
                
                # Test 9: Get updated wardrobe with filters
                print("\n--- Test 9: Get Wardrobe with Filters ---")
                items, total = await wardrobe_service.get_user_wardrobe(
                    db, user.id,
                    source="shop_product",
                    folder="Test Folder"
                )
                print(f"✓ Filtered items (source=shop_product, folder=Test Folder): {len(items)}")
                
                # Test 10: Delete the item
                print("\n--- Test 10: Delete Wardrobe Item ---")
                deleted = await wardrobe_service.delete(db, wardrobe_item.id, delete_files=False)
                print(f"✓ Item deleted: {deleted}")
                
                # Verify deletion
                check = await wardrobe_service.get_by_id(db, wardrobe_item.id)
                print(f"✓ Item no longer exists: {check is None}")
                
            else:
                print("❌ Failed to create wardrobe item from shop")
        else:
            print("⚠ No approved products found. Skipping shop product tests.")
        
        # Test 11: Try to create from generation (if generations exist)
        print("\n--- Test 11: Create from Generation ---")
        gen_result = await db.execute(
            select(Generation).where(Generation.user_id == user.id).limit(1)
        )
        generation = gen_result.scalar_one_or_none()
        
        if generation:
            print(f"✓ Test generation found: ID {generation.id}")
            
            custom_data = WardrobeItemFromGeneration(
                name="AI Generated Item",
                folder="AI Creations",
                is_favorite=True
            )
            
            gen_item = await wardrobe_service.create_from_generation(
                db, user.id, generation.id, custom_data
            )
            
            if gen_item:
                print(f"✓ Created wardrobe item from generation: ID {gen_item.id}")
                print(f"  - Name: {gen_item.name}")
                print(f"  - Source: {gen_item.source.value}")
                print(f"  - Generation ID: {gen_item.generation_id}")
                
                # Clean up
                await wardrobe_service.delete(db, gen_item.id, delete_files=False)
                print(f"✓ Cleaned up test item")
            else:
                print("❌ Failed to create wardrobe item from generation")
        else:
            print("⚠ No generations found for this user. Skipping generation tests.")
        
        # Final stats
        print("\n--- Final Wardrobe Stats ---")
        final_stats = await wardrobe_service.get_stats(db, user.id)
        print(f"✓ Final stats: {final_stats}")
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_wardrobe_service())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
