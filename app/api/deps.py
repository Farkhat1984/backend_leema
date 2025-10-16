from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.services.user_service import user_service
from app.services.shop_service import shop_service
from typing import Optional

security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current authenticated user (optional - returns None if not authenticated)
    Used for endpoints that work with or without authentication
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload or not payload.get("user_id"):
        return None
    
    # Validate account_type matches
    if payload.get("account_type") and payload.get("account_type") == "shop":
        return None

    user = await user_service.get_by_id(db, payload["user_id"])
    if not user:
        return None
    
    # Verify role matches token
    if payload.get("role") and payload["role"] != user.role.value:
        return None

    # Store platform info for guards to use
    user.token_platform = payload.get("platform")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user with enhanced token validation
    Validates: user_id, role, platform, account_type
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        print(f"[AUTH DEBUG] Token verification failed. Token: {token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if not payload.get("user_id"):
        print(f"[AUTH DEBUG] No user_id in payload. Payload: {payload}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials - no user_id",
        )
    
    # Validate account_type matches (prevent shop tokens being used as user)
    # Only enforce if account_type is present in token (for backward compatibility)
    if payload.get("account_type") and payload.get("account_type") == "shop":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shop credentials cannot be used for user endpoints"
        )

    user = await user_service.get_by_id(db, payload["user_id"])
    if not user:
        print(f"[AUTH DEBUG] User not found. user_id: {payload['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Verify role matches token (prevent role escalation)
    if payload.get("role") and payload["role"] != user.role.value:
        print(f"[AUTH SECURITY] Role mismatch! Token: {payload['role']}, DB: {user.role.value}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role mismatch - please re-login"
        )

    print(f"[AUTH DEBUG] User authenticated: {user.email} (id={user.id}, role={user.role.value}, platform={payload.get('platform', 'unknown')})")
    
    # Store platform info for guards to use
    user.token_platform = payload.get("platform")
    return user


async def get_current_shop(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Shop:
    """
    Get current authenticated shop with enhanced validation
    Prevents user tokens from accessing shop endpoints
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload or not payload.get("shop_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid shop authentication credentials",
        )
    
    # Validate account_type matches (prevent user tokens being used as shop)
    # Only enforce if account_type is present in token (for backward compatibility)
    if payload.get("account_type") and payload.get("account_type") != "shop":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User credentials cannot be used for shop endpoints"
        )

    shop = await shop_service.get_by_id(db, payload["shop_id"])
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Shop not found",
        )
    
    # Store platform info for guards
    shop.token_platform = payload.get("platform")
    return shop


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify current user is admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
