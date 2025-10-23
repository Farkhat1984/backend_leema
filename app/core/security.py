from datetime import timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.core.datetime_utils import utc_now
import asyncio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access", check_blacklist: bool = True) -> Optional[dict]:
    """
    Verify JWT token and return payload.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type (access/refresh)
        check_blacklist: Whether to check Redis blacklist (async operation)
    
    Returns:
        Token payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        
        # Check token blacklist (only for refresh tokens in async context)
        if check_blacklist and token_type == "refresh":
            # Note: This will be checked in the async endpoint
            pass
        
        return payload
    except JWTError:
        return None


async def verify_token_async(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Async version of verify_token that checks Redis blacklist.
    Use this in async endpoints that need blacklist checking.
    """
    try:
        # First verify token structure
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        
        # Check if token is blacklisted (refresh tokens only)
        if token_type == "refresh":
            from app.core.redis import redis_client
            is_blacklisted = await redis_client.is_token_blacklisted(token)
            if is_blacklisted:
                return None
        
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify access token - alias for verify_token"""
    return verify_token(token, token_type="access")


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against hash"""
    return pwd_context.verify(plain_password, hashed_password)
