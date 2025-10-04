"""
Advanced role and platform-based access control guards
Prevents privilege escalation and platform-specific conflicts
"""
from typing import List, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.api.deps import get_current_user, get_current_shop
from app.schemas.auth import ClientPlatform


class RoleChecker:
    """
    Role-based access control with hierarchy
    Hierarchy: admin > shop > user
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: User = Depends(get_current_user)):
        # Admin has access to everything (superuser)
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        if current_user.role.value not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


class PlatformChecker:
    """
    Platform-based access control
    Web: Admin and Shop only
    Mobile: All roles (user, shop as "regular")
    """
    def __init__(self, allowed_platforms: List[ClientPlatform]):
        self.allowed_platforms = allowed_platforms
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        x_client_platform: Optional[str] = Header(None)
    ):
        # Extract platform from token (already in current_user context if needed)
        # For now, use header as primary source
        if not x_client_platform:
            # If no header, assume mobile for backward compatibility
            x_client_platform = ClientPlatform.MOBILE.value
        
        try:
            platform = ClientPlatform(x_client_platform.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platform. Must be one of: {[p.value for p in ClientPlatform]}"
            )
        
        if platform not in self.allowed_platforms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied from {platform.value}. Allowed platforms: {[p.value for p in self.allowed_platforms]}"
            )
        
        # Web platform: only admin and shop
        if platform == ClientPlatform.WEB:
            if current_user.role == UserRole.USER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Regular users cannot access web platform. Use mobile app."
                )
        
        return current_user


class ShopOwnerChecker:
    """
    Verify that the current user is the shop owner or admin
    Prevents cross-shop manipulation
    """
    async def __call__(
        self,
        shop_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # Admin can access any shop
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # For shops, verify ownership via get_current_shop
        # This assumes shop authentication includes shop_id in token
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires shop authentication"
        )


class ShopAccessChecker:
    """
    Check shop-specific access with proper shop authentication
    """
    async def __call__(
        self,
        current_shop: Shop = Depends(get_current_shop),
        x_client_platform: Optional[str] = Header(None)
    ):
        # Shops should primarily use web platform
        if x_client_platform:
            try:
                platform = ClientPlatform(x_client_platform.lower())
                if platform == ClientPlatform.MOBILE:
                    # Allow mobile for shop profile viewing, but warn
                    pass  # Can be restricted further if needed
            except ValueError:
                pass
        
        return current_shop


class AdminOnlyChecker:
    """
    Strict admin-only access
    """
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        x_client_platform: Optional[str] = Header(None)
    ):
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator access required"
            )
        
        # Admin should use web platform
        if x_client_platform:
            try:
                platform = ClientPlatform(x_client_platform.lower())
                if platform != ClientPlatform.WEB:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Admin panel only accessible via web platform"
                    )
            except ValueError:
                pass
        
        return current_user


# Predefined guards for common use cases
require_user = RoleChecker([UserRole.USER.value])
require_admin = AdminOnlyChecker()
require_web_platform = PlatformChecker([ClientPlatform.WEB])
require_mobile_platform = PlatformChecker([ClientPlatform.MOBILE])
require_any_platform = PlatformChecker([ClientPlatform.WEB, ClientPlatform.MOBILE])
