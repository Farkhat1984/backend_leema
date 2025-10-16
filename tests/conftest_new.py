"""
Comprehensive pytest configuration and fixtures for all tests
"""
import pytest
import asyncio
import os
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.product import Product, ModerationStatus
from app.schemas.user import UserCreate
from app.schemas.shop import ShopCreate

# Test database URL (SQLite in memory for isolation)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Set testing environment
os.environ["TESTING"] = "1"
os.environ["DEBUG"] = "1"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> Generator:
    """Create test client with database override"""
    
    async def override_get_db():
        yield db_session
    
    # Mock the lifespan to skip startup/shutdown events
    @asynccontextmanager
    async def mock_lifespan(app):
        yield
    
    from app.main import app
    app.router.lifespan_context = mock_lifespan
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# User fixtures
@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    from app.services.user_service import user_service
    user_data = UserCreate(
        google_id="test_user_google_id",
        email="zfaragj@gmail.com",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg"
    )
    user = await user_service.create(db_session, user_data)
    user.balance = 100.0  # Give initial balance
    user.free_generations_left = 5
    user.free_try_ons_left = 5
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user"""
    from app.services.user_service import user_service
    user_data = UserCreate(
        google_id="admin_google_id",
        email="zfaragj@gmail.com",
        name="Admin User",
    )
    user = await user_service.create(db_session, user_data)
    user.role = UserRole.ADMIN
    user.balance = 1000.0
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_shop(db_session: AsyncSession) -> Shop:
    """Create a test shop"""
    from app.services.shop_service import shop_service
    shop_data = ShopCreate(
        google_id="test_shop_google_id",
        email="ckdshfh@gmail.com",
        shop_name="Test Shop",
        owner_name="Shop Owner",
        avatar_url="https://example.com/shop.jpg"
    )
    shop = await shop_service.create(db_session, shop_data)
    shop.balance = 500.0
    await db_session.commit()
    await db_session.refresh(shop)
    return shop


@pytest.fixture
async def test_product(db_session: AsyncSession, test_shop: Shop) -> Product:
    """Create a test product"""
    from app.services.product_service import product_service
    from app.schemas.product import ProductCreate
    
    product_data = ProductCreate(
        name="Test Product",
        description="Test product description",
        price=99.99,
        rental_price=19.99,
        rental_period_days=7,
        category="clothing",
        sizes=["S", "M", "L"],
        colors=["red", "blue"],
        images=["https://example.com/image1.jpg"]
    )
    product = await product_service.create(db_session, test_shop.id, product_data)
    product.moderation_status = ModerationStatus.APPROVED
    product.is_active = True
    await db_session.commit()
    await db_session.refresh(product)
    return product


# Token fixtures
@pytest.fixture
def user_token(test_user: User) -> str:
    """Create JWT token for test user"""
    return create_access_token({
        "user_id": test_user.id,
        "role": test_user.role.value,
        "account_type": "user"
    })


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create JWT token for admin user"""
    return create_access_token({
        "user_id": admin_user.id,
        "role": "admin",
        "account_type": "user"
    })


@pytest.fixture
def shop_token(test_shop: Shop) -> str:
    """Create JWT token for test shop"""
    return create_access_token({
        "shop_id": test_shop.id,
        "role": "shop",
        "account_type": "shop"
    })


# Header fixtures
@pytest.fixture
def user_headers(user_token: str) -> dict:
    """Create authorization headers for user"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Create authorization headers for admin"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def shop_headers(shop_token: str) -> dict:
    """Create authorization headers for shop"""
    return {"Authorization": f"Bearer {shop_token}"}


# PayPal credentials from .env
@pytest.fixture
def paypal_credentials() -> dict:
    """PayPal sandbox credentials"""
    return {
        "client_id": os.getenv("PAYPAL_CLIENT_ID", "ASFzSjsoyZ2FVCU9aCprMeTGjBr14DDN5i_6e52N6NuZ60Jk_4bLy2zKFiYTEHG9uOlZso52sAVaCUrG"),
        "client_secret": os.getenv("PAYPAL_CLIENT_SECRET", "EA5O0wQnrbK3XNz1ykm9H3Ac3IxNWWGDX4hPP8KTnuKCEkDuuNkW2L9CetC3MxXLLg0LI8Xr_4SDXsrt"),
        "mode": "sandbox",
        "test_email": "sb-0qexx39406981@business.example.com",
        "test_pass": "YPETl7&<"
    }


# Gemini API key
@pytest.fixture
def gemini_api_key() -> str:
    """Gemini API key for testing"""
    return os.getenv("GEMINI_API_KEY", "AIzaSyBkuZtWOZGfo3exgJovUO5s0DZ59dh2TmQ")
