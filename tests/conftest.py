"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock
from app.database import get_db
from app.core.security import create_access_token

# Test database URL (SQLite in memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def client():
    """Create test client without database connection"""
    # Import app here to avoid database connection on startup
    import os
    os.environ["TESTING"] = "1"
    
    # Mock the database dependency to avoid real DB connection
    async def mock_get_db():
        mock_db = MagicMock(spec=AsyncSession)
        yield mock_db
    
    from app.main import app
    
    # Mock the lifespan context manager
    @asynccontextmanager
    async def mock_lifespan(app):
        yield {}
    
    app.router.lifespan_context = mock_lifespan
    app.dependency_overrides[get_db] = mock_get_db
    
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_token():
    """Create test JWT token"""
    return create_access_token({"user_id": 1, "role": "user"})


@pytest.fixture
def admin_token():
    """Create admin JWT token"""
    return create_access_token({"user_id": 1, "role": "admin"})


@pytest.fixture
def auth_headers(test_token):
    """Create authorization headers"""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Create admin authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}
