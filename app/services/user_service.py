from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.generation import Generation
from app.schemas.user import UserCreate, UserUpdate
from app.services.settings_service import settings_service
from typing import Optional, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class UserService:
    """User service for business logic"""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_google_id(db: AsyncSession, google_id: str) -> Optional[User]:
        """Get user by Google ID"""
        result = await db.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user_data: UserCreate) -> User:
        """Create new user with free limits"""
        # Get free limits from settings
        free_generations = await settings_service.get_setting_int(
            db, "user_free_generations", 3
        )
        free_try_ons = await settings_service.get_setting_int(
            db, "user_free_try_ons", 5
        )

        user = User(
            google_id=user_data.google_id,
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            free_generations_left=free_generations,
            free_try_ons_left=free_try_ons,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"User created: {user.email}")
        return user

    @staticmethod
    async def update(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user"""
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return None

        if user_data.name:
            user.name = user_data.name
        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def add_balance(db: AsyncSession, user_id: int, amount: float) -> bool:
        """Add balance to user"""
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False

        user.balance = float(user.balance) + amount
        await db.commit()
        logger.info(f"Balance added to user {user_id}: +{amount}")
        return True

    @staticmethod
    async def get_transactions(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Transaction]:
        """Get user transactions"""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def charge_for_generation(db: AsyncSession, user_id: int) -> dict:
        """Charge user for AI generation - uses free credits first, then balance"""
        from app.services.settings_service import settings_service
        from app.models.transaction import Transaction, TransactionType, TransactionStatus

        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        # Check if user has free generations
        if user.free_generations_left > 0:
            user.free_generations_left -= 1
            await db.commit()
            logger.info(f"Used free generation for user {user_id}. Remaining: {user.free_generations_left}")
            return {
                "charged": False,
                "amount": 0,
                "free_remaining": user.free_generations_left,
                "message": "Использована бесплатная генерация"
            }

        # Get generation price from settings
        generation_price = await settings_service.get_setting_float(db, "user_generation_price", 1.0)
        generation_price_decimal = Decimal(str(generation_price))

        # Check user balance
        if user.balance < generation_price_decimal:
            raise ValueError(f"Недостаточно средств. Требуется: ${generation_price}, доступно: ${user.balance}. Пополните баланс.")

        # Charge user
        user.balance -= generation_price_decimal

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.GENERATION,
            amount=-generation_price_decimal,
            status=TransactionStatus.COMPLETED,
            extra_data={"description": "AI генерация изображения"}
        )
        db.add(transaction)

        await db.commit()
        logger.info(f"Charged user {user_id} ${generation_price} for generation")
        return {
            "charged": True,
            "amount": generation_price,
            "balance_remaining": user.balance,
            "message": f"Списано ${generation_price}"
        }

    @staticmethod
    async def charge_for_tryon(db: AsyncSession, user_id: int) -> dict:
        """Charge user for virtual try-on - uses free credits first, then balance"""
        from app.services.settings_service import settings_service
        from app.models.transaction import Transaction, TransactionType, TransactionStatus

        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        # Check if user has free try-ons
        if user.free_try_ons_left > 0:
            user.free_try_ons_left -= 1
            await db.commit()
            logger.info(f"Used free try-on for user {user_id}. Remaining: {user.free_try_ons_left}")
            return {
                "charged": False,
                "amount": 0,
                "free_remaining": user.free_try_ons_left,
                "message": "Использована бесплатная примерка"
            }

        # Get try-on price from settings
        tryon_price = await settings_service.get_setting_float(db, "user_tryon_price", 0.5)
        tryon_price_decimal = Decimal(str(tryon_price))

        # Check user balance
        if user.balance < tryon_price_decimal:
            raise ValueError(f"Недостаточно средств. Требуется: ${tryon_price}, доступно: ${user.balance}. Пополните баланс.")

        # Charge user
        user.balance -= tryon_price_decimal

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.TRY_ON,
            amount=-tryon_price_decimal,
            status=TransactionStatus.COMPLETED,
            extra_data={"description": "Виртуальная примерка"}
        )
        db.add(transaction)

        await db.commit()
        logger.info(f"Charged user {user_id} ${tryon_price} for try-on")
        return {
            "charged": True,
            "amount": tryon_price,
            "balance_remaining": user.balance,
            "message": f"Списано ${tryon_price}"
        }

    @staticmethod
    async def get_generations(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Generation]:
        """Get user generations/try-ons"""
        result = await db.execute(
            select(Generation)
            .where(Generation.user_id == user_id)
            .order_by(Generation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


user_service = UserService()
