"""
Redis client for caching, session storage, and token blacklist.
"""
from typing import Optional
import json
import logging
from redis.asyncio import Redis, ConnectionPool
from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with convenience methods"""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None
    
    async def connect(self):
        """Initialize Redis connection pool"""
        try:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=10
            )
            self._redis = Redis(connection_pool=self._pool)
            
            # Test connection
            await self._redis.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️ Running without Redis - features like token blacklist will be disabled")
            self._redis = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis disconnected")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is available"""
        return self._redis is not None
    
    # Token Blacklist Methods
    
    async def blacklist_token(self, token: str, expiry_seconds: int):
        """Add token to blacklist"""
        if not self._redis:
            return False
        try:
            await self._redis.setex(f"blacklist:token:{token}", expiry_seconds, "1")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        if not self._redis:
            return False
        try:
            result = await self._redis.exists(f"blacklist:token:{token}")
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False
    
    # Caching Methods
    
    async def get_cached(self, key: str) -> Optional[dict]:
        """Get cached value"""
        if not self._redis:
            return None
        try:
            value = await self._redis.get(f"cache:{key}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached value: {e}")
            return None
    
    async def set_cached(self, key: str, value: dict, ttl: int = 300):
        """Set cached value with TTL (default 5 minutes)"""
        if not self._redis:
            return False
        try:
            await self._redis.setex(
                f"cache:{key}",
                ttl,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set cached value: {e}")
            return False
    
    async def delete_cached(self, key: str):
        """Delete cached value"""
        if not self._redis:
            return False
        try:
            await self._redis.delete(f"cache:{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cached value: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        if not self._redis:
            return False
        try:
            keys = []
            async for key in self._redis.scan_iter(f"cache:{pattern}*"):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern: {e}")
            return False
    
    # Rate Limiting Methods
    
    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is within rate limit.
        Returns True if allowed, False if rate limit exceeded.
        """
        if not self._redis:
            return True  # Allow if Redis unavailable
        
        try:
            cache_key = f"ratelimit:{key}"
            current = await self._redis.get(cache_key)
            
            if current is None:
                # First request in window
                await self._redis.setex(cache_key, window_seconds, "1")
                return True
            
            count = int(current)
            if count >= max_requests:
                return False
            
            # Increment counter
            await self._redis.incr(cache_key)
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow on error
    
    # Session Storage Methods
    
    async def set_session(self, session_id: str, data: dict, ttl: int = 3600):
        """Store session data"""
        if not self._redis:
            return False
        try:
            await self._redis.setex(
                f"session:{session_id}",
                ttl,
                json.dumps(data)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data"""
        if not self._redis:
            return None
        try:
            value = await self._redis.get(f"session:{session_id}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def delete_session(self, session_id: str):
        """Delete session"""
        if not self._redis:
            return False
        try:
            await self._redis.delete(f"session:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False


# Singleton instance
redis_client = RedisClient()


# Convenience functions
async def init_redis():
    """Initialize Redis connection on startup"""
    await redis_client.connect()


async def close_redis():
    """Close Redis connection on shutdown"""
    await redis_client.disconnect()
