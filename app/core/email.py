import aiosmtplib
from email.message import EmailMessage
from jinja2 import Template
from app.config import settings
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email notification service"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.email_from_name = settings.EMAIL_FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """Send email"""
        try:
            message = EmailMessage()
            message["From"] = f"{self.email_from_name} <{self.email_from}>"
            message["To"] = to_email
            message["Subject"] = subject

            if html:
                message.add_alternative(body, subtype="html")
            else:
                message.set_content(body)

            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=True,
            )

            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

    async def send_rent_expiring_notification(
        self,
        to_email: str,
        shop_name: str,
        product_name: str,
        expires_in_days: int
    ) -> bool:
        """Send notification about product rent expiring"""
        subject = f"Product Rent Expiring Soon - {product_name}"

        html_template = Template("""
        <html>
            <body>
                <h2>Hello {{ shop_name }},</h2>
                <p>Your product <strong>{{ product_name }}</strong> rent will expire in <strong>{{ expires_in_days }} days</strong>.</p>
                <p>Please renew the rent to keep your product active on the platform.</p>
                <p>Best regards,<br>{{ app_name }} Team</p>
            </body>
        </html>
        """)

        body = html_template.render(
            shop_name=shop_name,
            product_name=product_name,
            expires_in_days=expires_in_days,
            app_name=settings.APP_NAME
        )

        return await self.send_email(to_email, subject, body, html=True)

    async def send_product_approved_notification(
        self,
        to_email: str,
        shop_name: str,
        product_name: str
    ) -> bool:
        """Send notification about product approval"""
        subject = f"Product Approved - {product_name}"

        html_template = Template("""
        <html>
            <body>
                <h2>Hello {{ shop_name }},</h2>
                <p>Your product <strong>{{ product_name }}</strong> has been approved!</p>
                <p>It is now visible to users on the platform.</p>
                <p>Best regards,<br>{{ app_name }} Team</p>
            </body>
        </html>
        """)

        body = html_template.render(
            shop_name=shop_name,
            product_name=product_name,
            app_name=settings.APP_NAME
        )

        return await self.send_email(to_email, subject, body, html=True)

    async def send_product_rejected_notification(
        self,
        to_email: str,
        shop_name: str,
        product_name: str,
        reason: str
    ) -> bool:
        """Send notification about product rejection"""
        subject = f"Product Rejected - {product_name}"

        html_template = Template("""
        <html>
            <body>
                <h2>Hello {{ shop_name }},</h2>
                <p>Your product <strong>{{ product_name }}</strong> has been rejected.</p>
                <p><strong>Reason:</strong> {{ reason }}</p>
                <p>Please update your product and resubmit for approval.</p>
                <p>Best regards,<br>{{ app_name }} Team</p>
            </body>
        </html>
        """)

        body = html_template.render(
            shop_name=shop_name,
            product_name=product_name,
            reason=reason,
            app_name=settings.APP_NAME
        )

        return await self.send_email(to_email, subject, body, html=True)


email_service = EmailService()
