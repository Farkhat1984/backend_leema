from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks.rent_checker import check_expiring_rents, deactivate_expired_products
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Start background task scheduler"""
    # Check expiring rents daily at 9 AM
    scheduler.add_job(
        check_expiring_rents,
        CronTrigger(hour=9, minute=0),
        id="check_expiring_rents",
        name="Check expiring product rents",
        replace_existing=True
    )

    # Deactivate expired products daily at 0:00 AM
    scheduler.add_job(
        deactivate_expired_products,
        CronTrigger(hour=0, minute=0),
        id="deactivate_expired_products",
        name="Deactivate expired products",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop background task scheduler"""
    scheduler.shutdown()
    logger.info("Background scheduler stopped")
