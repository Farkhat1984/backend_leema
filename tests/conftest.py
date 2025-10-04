"""
Pytest configuration and fixtures for testing Fashion AI Platform API
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.services.user_service import user_service
from app.services.shop_service import shop_service
from app.core.security import create_access_token


# Create test database engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests"""
    return "asyncio"


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with test_session_maker() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user"""
    from app.schemas.user import UserCreate

    user_data = UserCreate(
        google_id="test_user_123",
        email="testuser@example.com",
        name="Test User",
    )
    user = await user_service.create(db_session, user_data)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user"""
    from app.schemas.user import UserCreate

    user_data = UserCreate(
        google_id="test_admin_123",
        email="testadmin@example.com",
        name="Test Admin",
    )
    admin = await user_service.create(db_session, user_data)
    admin.role = UserRole.ADMIN
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def test_shop(db_session: AsyncSession) -> Shop:
    """Create test shop"""
    from app.schemas.shop import ShopCreate

    shop_data = ShopCreate(
        google_id="test_shop_123",
        email="testshop@example.com",
        shop_name="Test Shop",
        owner_name="Test Owner"
    )
    shop = await shop_service.create(db_session, shop_data)
    await db_session.commit()
    await db_session.refresh(shop)
    return shop


@pytest.fixture
def user_token(test_user: User) -> str:
    """Create JWT token for test user"""
    return create_access_token({
        "user_id": test_user.id,
        "role": test_user.role.value,
        "account_type": "user",
        "platform": "mobile"
    })


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """Create JWT token for test admin"""
    return create_access_token({
        "user_id": test_admin.id,
        "role": test_admin.role.value,
        "account_type": "user",
        "platform": "mobile"
    })


@pytest.fixture
def shop_token(test_shop: Shop) -> str:
    """Create JWT token for test shop"""
    return create_access_token({
        "shop_id": test_shop.id,
        "account_type": "shop",
        "platform": "mobile"
    })


@pytest.fixture
async def test_product(db_session: AsyncSession, test_shop: Shop):
    """Create test product"""
    from app.schemas.product import ProductCreate
    from app.services.product_service import product_service
    from datetime import datetime, timedelta, timezone

    product_data = ProductCreate(
        name="Test Product",
        description="Test Description",
        price=99.99,
        images=["https://example.com/image.jpg"]
    )
    product = await product_service.create(db_session, test_shop.id, product_data)

    # Approve and activate product for testing
    product.moderation_status = "approved"
    product.is_active = True
    product.rent_start_date = datetime.now(timezone.utc)
    product.rent_end_date = datetime.now(timezone.utc) + timedelta(days=30)

    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
def auth_headers_user(user_token: str) -> dict:
    """Create authorization headers for user"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def auth_headers_admin(admin_token: str) -> dict:
    """Create authorization headers for admin"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_shop(shop_token: str) -> dict:
    """Create authorization headers for shop"""
    return {"Authorization": f"Bearer {shop_token}"}
