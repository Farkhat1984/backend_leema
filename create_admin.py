"""
Script to create admin user
Run after you've registered via Google OAuth
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User, UserRole


async def make_admin(email: str):
    """Make user admin by email"""
    # Create async engine
    engine = create_async_engine("sqlite+aiosqlite:///./fashion_platform.db")
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
