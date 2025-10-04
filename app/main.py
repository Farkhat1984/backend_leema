from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings
from app.database import init_db, close_db
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.services.settings_service import settings_service
from app.database import async_session_maker

# Import routers
from app.api import auth, users, shops, products, payments, generations, admin

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

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Fashion AI Platform API - Generate, try-on, and shop for fashion items",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - must be added BEFORE other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Mount static files (uploads)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount frontend static files (HTML/CSS/JS)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    # Mount assets directory for CSS/JS files
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info(f"Mounted assets from {assets_dir}")
    
    # Mount static directory for other files
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static files from {static_dir}")

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(shops.router, prefix=f"{settings.API_V1_PREFIX}/shops", tags=["Shops"])
app.include_router(products.router, prefix=f"{settings.API_V1_PREFIX}/products", tags=["Products"])
app.include_router(payments.router, prefix=f"{settings.API_V1_PREFIX}/payments", tags=["Payments"])
app.include_router(generations.router, prefix=f"{settings.API_V1_PREFIX}/generations", tags=["Generations"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])


from fastapi.responses import FileResponse

@app.get("/")
async def root():
    """Redirect to shop page"""
    static_index = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "shop.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/index.html")
async def index_page():
    """Serve index.html"""
    static_index = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {"error": "Frontend not found"}

@app.get("/shop.html")
async def shop_page():
    """Serve shop.html"""
    static_shop = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "shop.html")
    if os.path.exists(static_shop):
        return FileResponse(static_shop)
    return {"error": "Frontend not found"}

@app.get("/admin.html")
async def admin_page():
    """Serve admin.html"""
    static_admin = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "admin.html")
    if os.path.exists(static_admin):
        return FileResponse(static_admin)
    return {"error": "Frontend not found"}

@app.get("/topup.html")
async def topup_page():
    """Serve topup.html"""
    static_topup = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "topup.html")
    if os.path.exists(static_topup):
        return FileResponse(static_topup)
    return {"error": "Frontend not found"}

@app.get("/callback.html")
async def callback_page():
    """Serve callback.html"""
    static_callback = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "callback.html")
    if os.path.exists(static_callback):
        return FileResponse(static_callback)
    return {"error": "Frontend not found"}


@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity check"""
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
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
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
