from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging
import os
import json

from app.config import settings
from app.database import init_db, close_db
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.services.settings_service import settings_service
from app.database import async_session_maker
from app.core.websocket import connection_manager
from app.core.security import decode_access_token, verify_token_async
from app.core.redis import init_redis, close_redis
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import routers
from app.api import auth, users, shops, products, payments, generations, admin, cart, orders, analytics, categories, wardrobe

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Reduce SQLAlchemy log verbosity
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_PER_MINUTE])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Fashion AI Platform API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis
    await init_redis()
    logger.info("Redis initialized")

    # Initialize default settings
    async with async_session_maker() as db:
        await settings_service.initialize_default_settings(db)

    # Start background scheduler
    start_scheduler()

    # Create upload directories
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/products", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/generations", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/shops", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/users", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/temp", exist_ok=True)

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    await close_redis()
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app
# Disable docs in production for security
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Fashion AI Platform API - Generate, try-on, and shop for fashion items",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable Swagger UI in production
    redoc_url="/redoc" if settings.DEBUG else None,  # Disable ReDoc in production
    openapi_url="/openapi.json" if settings.DEBUG else None  # Disable OpenAPI schema in production
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - must be added BEFORE other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Use production origins from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Mount static files (uploads)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Frontend static files removed - frontend should be served separately

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(shops.router, prefix=f"{settings.API_V1_PREFIX}/shops", tags=["Shops"])
app.include_router(categories.router, prefix=f"{settings.API_V1_PREFIX}/categories", tags=["Categories"])
app.include_router(products.router, prefix=f"{settings.API_V1_PREFIX}/products", tags=["Products"])
app.include_router(wardrobe.router, prefix=f"{settings.API_V1_PREFIX}/wardrobe", tags=["Wardrobe"])
app.include_router(cart.router, prefix=f"{settings.API_V1_PREFIX}/cart", tags=["Cart"])
app.include_router(orders.router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["Orders"])
app.include_router(payments.router, prefix=f"{settings.API_V1_PREFIX}/payments", tags=["Payments"])
app.include_router(generations.router, prefix=f"{settings.API_V1_PREFIX}/generations", tags=["Generations"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])


@app.get("/")
async def root():
    """API root - frontend should be served separately"""
    response = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

    # Only show docs links in development
    if settings.DEBUG:
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"

    return response


@app.get("/api/v1/config")
async def get_client_config():
    """
    Get client configuration for mobile apps
    Returns API and WebSocket URLs
    """
    return {
        "api_base_url": settings.API_BASE_URL,
        "websocket_url": settings.WEBSOCKET_URL,
        "api_version": "v1",
        "endpoints": {
            "websocket_user": f"{settings.WEBSOCKET_URL}/ws/user",
            "websocket_shop": f"{settings.WEBSOCKET_URL}/ws/shop",
            "websocket_admin": f"{settings.WEBSOCKET_URL}/ws/admin",
            "websocket_products": f"{settings.WEBSOCKET_URL}/ws/products"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity check"""
    from sqlalchemy import text

    health_status = {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

    # Check database connection
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"disconnected: {str(e)}"
        logger.error(f"Health check failed: {e}")

    # Add WebSocket connection stats
    health_status["websocket_connections"] = connection_manager.get_connection_count()

    return health_status


@app.websocket("/ws")
async def websocket_web_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    client_type: str = Query(...),
    platform: str = Query("web")
):
    """
    WebSocket endpoint for web platform (client_type as query param)
    
    Parameters:
    - token: JWT access token for authentication
    - client_type: 'user', 'shop', or 'admin'
    - platform: 'web' (default) or 'mobile'
    
    Usage:
    ws://localhost:8000/ws?token=YOUR_JWT_TOKEN&client_type=shop&platform=web
    wss://api.leema.kz/ws?token=YOUR_JWT_TOKEN&client_type=admin&platform=web
    """
    logger.info(f"🌐 Web WebSocket connection: client_type={client_type}, platform={platform}")
    
    # Check origin header for CORS (web browsers only)
    origin = websocket.headers.get("origin")
    if origin:
        allowed = False
        for allowed_origin in settings.CORS_ORIGINS:
            if origin == allowed_origin or origin.startswith(allowed_origin):
                allowed = True
                break
        
        if not allowed:
            logger.warning(f"❌ WebSocket connection rejected - invalid origin: {origin}")
            await websocket.close(code=1008)  # Policy Violation
            return
    
    # Verify token and get user/shop
    try:
        payload = await verify_token_async(token, "access")
        if not payload:
            logger.warning("❌ WebSocket authentication failed - invalid token")
            await websocket.close(code=1008)  # Policy Violation
            return
        
        account_id = payload.get("user_id") or payload.get("shop_id") or payload.get("sub")
        account_type = payload.get("account_type")
        
        # Validate client_type matches account_type or is admin
        if client_type == "admin":
            # For admin, check if user has admin role
            async with async_session_maker() as db:
                result = await db.execute(
                    select(User).where(User.id == account_id)
                )
                user = result.scalar_one_or_none()
                if not user or user.role != "admin":
                    logger.warning(f"❌ WebSocket rejected - user {account_id} is not admin")
                    await websocket.close(code=1008)
                    return
        elif client_type != account_type:
            logger.warning(f"❌ WebSocket rejected - client_type mismatch: {client_type} != {account_type}")
            await websocket.close(code=1008)
            return
        
        # Accept connection
        await connection_manager.connect(websocket, client_type, account_id, platform)
        logger.info(f"✅ WebSocket connected: {client_type}/{account_id} (platform: {platform})")
        
        try:
            while True:
                # Keep connection alive and handle messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping/pong
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })
                
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)
            logger.info(f"🔌 WebSocket disconnected: {client_type}/{account_id}")
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")
            connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"❌ WebSocket setup failed: {e}")
        await websocket.close(code=1011)  # Internal Error


@app.websocket("/ws/{client_type}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_type: str,
    token: str = Query(...),
    platform: str = Query("web")
):
    """
    WebSocket endpoint for real-time updates

    Parameters:
    - client_type: 'user', 'shop', or 'admin'
    - token: JWT access token for authentication
    - platform: 'mobile' or 'web' (optional, default: 'web')

    Usage:
    ws://localhost:8000/ws/shop?token=YOUR_JWT_TOKEN&platform=mobile
    wss://api.leema.kz/ws/shop?token=YOUR_JWT_TOKEN&platform=mobile
    """
    logger.info(f"📱 WebSocket connection attempt: client_type={client_type}, platform={platform}")
    
    # Check origin header for CORS (web browsers only)
    # Mobile apps typically don't send Origin header
    origin = websocket.headers.get("origin")
    if origin:
        # Check if origin is allowed
        allowed = False
        for allowed_origin in settings.CORS_ORIGINS:
            if origin == allowed_origin or origin.startswith(allowed_origin):
                allowed = True
                break
        
        # Also allow localhost origins in debug mode
        if settings.DEBUG and (
            origin.startswith("http://localhost") or 
            origin.startswith("http://127.0.0.1") or
            origin.startswith("http://192.168.")
        ):
            allowed = True
        
        if not allowed:
            logger.warning(f"❌ WebSocket connection rejected: origin {origin} not allowed")
            await websocket.close(code=1008, reason="Origin not allowed")
            return
    else:
        # No origin header - likely mobile app or direct connection
        logger.info(f"📱 WebSocket connection without origin header (likely mobile app, platform={platform})")
    
    # Validate client type
    if client_type not in ["user", "shop", "admin"]:
        logger.error(f"❌ Invalid client type: {client_type}")
        await websocket.close(code=1008, reason="Invalid client type")
        return

    # Authenticate user
    try:
        payload = decode_access_token(token)
        if not payload:
            logger.error("❌ Invalid token: decode returned None")
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Extract ID based on client type
        if client_type == "user":
            client_id = payload.get("user_id")
        elif client_type == "shop":
            client_id = payload.get("shop_id")
        elif client_type == "admin":
            client_id = payload.get("user_id")  # Admins are users with admin role
        else:
            logger.error(f"❌ Invalid client type in auth: {client_type}")
            await websocket.close(code=1008, reason="Invalid client type")
            return

        if not client_id:
            logger.error(f"❌ Token missing required ID for client_type={client_type}. Token payload: user_id={payload.get('user_id')}, shop_id={payload.get('shop_id')}, role={payload.get('role')}")
            await websocket.close(code=1008, reason="Invalid token payload")
            return

    except Exception as e:
        logger.error(f"❌ WebSocket authentication error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Log platform for analytics
    logger.info(f"✅ WebSocket authenticated: client_type={client_type}, client_id={client_id}, platform={platform}")
    
    # Connect client
    await connection_manager.connect(websocket, client_type, client_id)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., ping/pong, subscriptions)
                data = await websocket.receive_json()

                # Handle client commands
                if data.get("type") == "ping":
                    await connection_manager.send_personal_message(
                        {"type": "pong", "timestamp": data.get("timestamp")},
                        websocket
                    )
                elif data.get("type") == "subscribe_room":
                    room_name = data.get("room")
                    if room_name:
                        await connection_manager.join_room(websocket, room_name)
                        await connection_manager.send_personal_message(
                            {"type": "subscribed", "room": room_name},
                            websocket
                        )
                elif data.get("type") == "unsubscribe_room":
                    room_name = data.get("room")
                    if room_name:
                        await connection_manager.leave_room(websocket, room_name)
                        await connection_manager.send_personal_message(
                            {"type": "unsubscribed", "room": room_name},
                            websocket
                        )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")

    finally:
        connection_manager.disconnect(websocket, client_type, client_id)


@app.websocket("/ws/products")
async def websocket_products_alias(
    websocket: WebSocket,
    token: str = Query(...),
    client_type: str = Query("shop"),
    platform: str = Query("mobile")
):
    """
    WebSocket endpoint alias for products (mobile compatibility)
    
    This is an alias for /ws/shop endpoint to support mobile apps
    that connect to /ws/products
    
    Parameters:
    - token: JWT access token for authentication
    - client_type: 'shop' (default), 'user', or 'admin'
    - platform: 'mobile' (default) or 'web'
    
    Usage:
    wss://api.leema.kz/ws/products?token=YOUR_JWT_TOKEN&client_type=shop&platform=mobile
    """
    # Redirect to main websocket endpoint logic
    await websocket_endpoint(websocket, client_type, token, platform)


@app.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics (for monitoring)"""
    return connection_manager.get_connection_count()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
