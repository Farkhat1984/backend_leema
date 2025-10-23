#!/usr/bin/env python3
"""
Migration script to reorganize uploads directory structure
From: flat structure (products/, generations/, shop_images/)
To: hierarchical structure (shops/{id}/products/{id}/, users/{id}/wardrobe/, generations/{user_id}/)

Usage:
    python scripts/migrate_uploads.py --dry-run  # Preview changes
    python scripts/migrate_uploads.py --execute  # Execute migration
"""

import os
import sys
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session_maker
from app.models import Product, Generation, Shop, User


class UploadMigrator:
    def __init__(self, base_path: str, dry_run: bool = True):
        self.base_path = Path(base_path)
        self.dry_run = dry_run
        self.stats = {
            'products_moved': 0,
            'generations_moved': 0,
            'shop_images_moved': 0,
            'errors': 0
        }
    
    async def migrate_products(self):
        """Migrate products from /uploads/products/ to /uploads/shops/{shop_id}/products/{product_id}/"""
        print("\n📦 Migrating product images...")
        
        old_dir = self.base_path / "products"
        if not old_dir.exists():
            print(f"  ⚠️  Directory {old_dir} not found, skipping")
            return
        
        async with async_session_maker() as db:
            # Get all products with their shop_id
            stmt = select(Product).where(Product.images.isnot(None))
            result = await db.execute(stmt)
            products = result.scalars().all()
            
            print(f"  Found {len(products)} products to migrate")
            
            for product in products:
                try:
                    if not product.images:
                        continue
                    
                    # Create new directory structure
                    new_dir = self.base_path / "shops" / str(product.shop_id) / "products" / str(product.id)
                    
                    # Track files to update in database
                    new_images = []
                    files_moved = 0
                    
                    for idx, old_url in enumerate(product.images):
                        # Parse old path
                        if not old_url.startswith('/uploads/products/'):
                            new_images.append(old_url)  # Already migrated or external
                            continue
                        
                        old_file_name = old_url.split('/')[-1]
                        old_file_path = self.base_path / "products" / old_file_name
                        
                        if not old_file_path.exists():
                            print(f"    ⚠️  File not found: {old_file_path}")
                            new_images.append(old_url)  # Keep old URL
                            continue
                        
                        # New path with index
                        ext = old_file_path.suffix
                        new_file_name = f"image_{idx}{ext}"
                        new_file_path = new_dir / new_file_name
                        new_url = f"/uploads/shops/{product.shop_id}/products/{product.id}/{new_file_name}"
                        
                        if self.dry_run:
                            print(f"    [DRY RUN] Would move:")
                            print(f"      From: {old_file_path}")
                            print(f"      To:   {new_file_path}")
                        else:
                            # Create directory
                            new_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Copy file (not move, to be safe)
                            shutil.copy2(old_file_path, new_file_path)
                            files_moved += 1
                        
                        new_images.append(new_url)
                    
                    # Update database
                    if not self.dry_run and files_moved > 0:
                        product.images = new_images
                        await db.commit()
                        self.stats['products_moved'] += files_moved
                        print(f"    ✅ Migrated product {product.id}: {files_moved} files")
                    elif self.dry_run:
                        print(f"    [DRY RUN] Would update product {product.id} with {len(new_images)} images")
                
                except Exception as e:
                    print(f"    ❌ Error migrating product {product.id}: {e}")
                    self.stats['errors'] += 1
        
        print(f"  ✅ Products migration complete: {self.stats['products_moved']} files moved")
    
    async def migrate_generations(self):
        """Migrate generations from /uploads/generations/ to /uploads/generations/{user_id}/"""
        print("\n🎨 Migrating generation images...")
        
        old_dir = self.base_path / "generations"
        if not old_dir.exists():
            print(f"  ⚠️  Directory {old_dir} not found, skipping")
            return
        
        async with async_session_maker() as db:
            # Get all generations
            stmt = select(Generation).where(Generation.image_url.isnot(None))
            result = await db.execute(stmt)
            generations = result.scalars().all()
            
            print(f"  Found {len(generations)} generations to migrate")
            
            for generation in generations:
                try:
                    if not generation.image_url:
                        continue
                    
                    # Parse old path
                    old_url = generation.image_url
                    if not old_url.startswith('/uploads/generations/'):
                        continue  # Already migrated or external
                    
                    # Check if already in user subdirectory
                    parts = old_url.split('/')
                    if len(parts) > 4 and parts[3].isdigit():
                        continue  # Already migrated (has user_id in path)
                    
                    old_file_name = old_url.split('/')[-1]
                    old_file_path = self.base_path / "generations" / old_file_name
                    
                    if not old_file_path.exists():
                        print(f"    ⚠️  File not found: {old_file_path}")
                        continue
                    
                    # New path with user_id subdirectory
                    new_dir = self.base_path / "generations" / str(generation.user_id)
                    new_file_path = new_dir / old_file_name
                    new_url = f"/uploads/generations/{generation.user_id}/{old_file_name}"
                    
                    if self.dry_run:
                        print(f"    [DRY RUN] Would move:")
                        print(f"      From: {old_file_path}")
                        print(f"      To:   {new_file_path}")
                    else:
                        # Create directory
                        new_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file
                        shutil.copy2(old_file_path, new_file_path)
                        
                        # Update database
                        generation.image_url = new_url
                        await db.commit()
                        
                        self.stats['generations_moved'] += 1
                        print(f"    ✅ Migrated generation {generation.id}")
                
                except Exception as e:
                    print(f"    ❌ Error migrating generation {generation.id}: {e}")
                    self.stats['errors'] += 1
        
        print(f"  ✅ Generations migration complete: {self.stats['generations_moved']} files moved")
    
    async def migrate_shop_images(self):
        """Migrate shop images from /uploads/shop_images/ to /uploads/shops/{shop_id}/avatar.*"""
        print("\n🏪 Migrating shop avatar images...")
        
        old_dir = self.base_path / "shop_images"
        if not old_dir.exists():
            print(f"  ⚠️  Directory {old_dir} not found, skipping")
            return
        
        async with async_session_maker() as db:
            # Get all shops
            stmt = select(Shop).where(Shop.avatar_url.isnot(None))
            result = await db.execute(stmt)
            shops = result.scalars().all()
            
            print(f"  Found {len(shops)} shops to migrate")
            
            for shop in shops:
                try:
                    if not shop.avatar_url:
                        continue
                    
                    # Parse old path
                    old_url = shop.avatar_url
                    if not old_url.startswith('/uploads/shop_images/'):
                        continue  # Already migrated or external
                    
                    old_file_name = old_url.split('/')[-1]
                    old_file_path = self.base_path / "shop_images" / old_file_name
                    
                    if not old_file_path.exists():
                        print(f"    ⚠️  File not found: {old_file_path}")
                        continue
                    
                    # New path
                    ext = old_file_path.suffix
                    new_dir = self.base_path / "shops" / str(shop.id)
                    new_file_name = f"avatar{ext}"
                    new_file_path = new_dir / new_file_name
                    new_url = f"/uploads/shops/{shop.id}/{new_file_name}"
                    
                    if self.dry_run:
                        print(f"    [DRY RUN] Would move:")
                        print(f"      From: {old_file_path}")
                        print(f"      To:   {new_file_path}")
                    else:
                        # Create directory
                        new_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file
                        shutil.copy2(old_file_path, new_file_path)
                        
                        # Update database
                        shop.avatar_url = new_url
                        await db.commit()
                        
                        self.stats['shop_images_moved'] += 1
                        print(f"    ✅ Migrated shop {shop.id} avatar")
                
                except Exception as e:
                    print(f"    ❌ Error migrating shop {shop.id} avatar: {e}")
                    self.stats['errors'] += 1
        
        print(f"  ✅ Shop images migration complete: {self.stats['shop_images_moved']} files moved")
    
    async def cleanup_old_files(self):
        """Remove old files after successful migration"""
        if self.dry_run:
            print("\n🧹 [DRY RUN] Would clean up old directories")
            return
        
        print("\n🧹 Cleaning up old files...")
        print("  ⚠️  This will DELETE old files. Ctrl+C to cancel, Enter to continue...")
        input()
        
        old_dirs = [
            self.base_path / "products",
            self.base_path / "shop_images"
        ]
        
        for old_dir in old_dirs:
            if old_dir.exists():
                try:
                    # Move to backup first
                    backup_dir = old_dir.parent / f"{old_dir.name}_backup"
                    shutil.move(str(old_dir), str(backup_dir))
                    print(f"  ✅ Moved {old_dir} to {backup_dir}")
                except Exception as e:
                    print(f"  ❌ Error cleaning up {old_dir}: {e}")
        
        print("  ℹ️  Old directories backed up. Remove manually after verification.")
    
    async def run(self, cleanup: bool = False):
        """Run full migration"""
        print("=" * 60)
        print("  FASHION AI PLATFORM - UPLOADS MIGRATION")
        print("=" * 60)
        print(f"Mode: {'DRY RUN (no changes)' if self.dry_run else 'EXECUTE (will modify)'}")
        print(f"Base path: {self.base_path}")
        print("=" * 60)
        
        await self.migrate_products()
        await self.migrate_generations()
        await self.migrate_shop_images()
        
        if cleanup and not self.dry_run:
            await self.cleanup_old_files()
        
        print("\n" + "=" * 60)
        print("  MIGRATION SUMMARY")
        print("=" * 60)
        print(f"  Products moved:      {self.stats['products_moved']}")
        print(f"  Generations moved:   {self.stats['generations_moved']}")
        print(f"  Shop images moved:   {self.stats['shop_images_moved']}")
        print(f"  Errors:              {self.stats['errors']}")
        print("=" * 60)
        
        if self.dry_run:
            print("\n✅ Dry run complete. Run with --execute to apply changes.")
        else:
            print("\n✅ Migration complete!")


def main():
    parser = argparse.ArgumentParser(description="Migrate uploads directory structure")
    parser.add_argument("--execute", action="store_true", help="Execute migration (default: dry-run)")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old directories after migration")
    parser.add_argument("--base-path", default="uploads", help="Base uploads directory path")
    
    args = parser.parse_args()
    
    migrator = UploadMigrator(
        base_path=args.base_path,
        dry_run=not args.execute
    )
    
    asyncio.run(migrator.run(cleanup=args.cleanup))


if __name__ == "__main__":
    main()
