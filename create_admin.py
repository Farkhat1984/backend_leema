"""
Script to create admin user
Run after you've registered via Google OAuth

Usage:
    python create_admin.py <email>

Example:
    python create_admin.py admin@example.com

Or with Docker:
    docker-compose exec backend python create_admin.py admin@example.com
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User, UserRole
from app.config import settings


async def make_admin(email: str):
    """Make user admin by email"""
    # Create async engine from settings (uses DATABASE_URL from .env)
    print(f"📊 Connecting to database...")
    print(f"   Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find user by email
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User with email {email} not found!")
            print("Please register first via Google OAuth")
            return

        # Update role to admin
        user.role = UserRole.ADMIN
        await session.commit()

        print(f"✅ User {email} is now ADMIN!")
        print(f"   ID: {user.id}")
        print(f"   Name: {user.name}")
        print(f"   Role: {user.role.value}")

        # Generate access token for testing
        from app.core.security import create_access_token
        token = create_access_token({"user_id": user.id})
        print(f"\n🔑 Access Token для Swagger UI:")
        print(f"   {token}")
        print(f"\n📝 В Swagger нажмите 'Authorize' и вставьте:")
        print(f"   Bearer {token}")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_admin.py <email>")
        print("Example: python create_admin.py admin@example.com")
        sys.exit(1)

    email = sys.argv[1]
    asyncio.run(make_admin(email))
