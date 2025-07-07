# app/utils/email.py
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import logging
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Setup Jinja2 environment for email templates
template_env = Environment(loader=FileSystemLoader("app/templates"))

async def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    fail_silently: bool = True
) -> bool:
    """Send email using template"""
    try:
        # Skip email sending in development if no email config
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            logger.info(f"EMAIL SKIPPED (no config): {subject} to {to_email}")
            if template_name == "verification_email":
                logger.info(f"VERIFICATION CODE: {context.get('verification_code')}")
            elif template_name == "password_reset":
                logger.info(f"RESET CODE: {context.get('reset_code')}")
            return True
        
        # Add common context
        context.update({
            'company_name': settings.COMPANY_NAME,
            'frontend_url': settings.FRONTEND_URL,
            'current_year': datetime.now().year,
        })
        
        # Render email template
        template = template_env.get_template(f"emails/{template_name}.html")
        html_content = template.render(**context)
        
        # Try to get text template
        try:
            text_template = template_env.get_template(f"emails/{template_name}.txt")
            text_content = text_template.render(**context)
        except:
            # Fallback to HTML stripped of tags
            import re
            text_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"[{settings.COMPANY_NAME}] {subject}"
        message["From"] = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        message["To"] = to_email
        
        # Add text and HTML parts
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")
        message.attach(text_part)
        message.attach(html_part)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            start_tls=settings.EMAIL_USE_TLS,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
        )
        
        logger.info(f"Email sent: {subject} to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        if not fail_silently:
            raise
        return False

async def send_verification_email(email: str, verification_code: str, user_name: str = None) -> bool:
    """Send email verification code"""
    context = {
        'verification_code': verification_code,
        'user_name': user_name,
        'expiry_hours': 24,
        'verification_url': f"{settings.FRONTEND_URL}/verify-email?code={verification_code}&email={email}"
    }
    
    return await send_email(
        to_email=email,
        subject="Verify Your Email Address",
        template_name="verification_email",
        context=context
    )

async def send_password_reset_email(email: str, reset_code: str, user_name: str = None) -> bool:
    """Send password reset code"""
    context = {
        'reset_code': reset_code,
        'user_name': user_name,
        'expiry_hours': 1,
        'reset_url': f"{settings.FRONTEND_URL}/reset-password?code={reset_code}&email={email}"
    }
    
    return await send_email(
        to_email=email,
        subject="Reset Your Password",
        template_name="password_reset",
        context=context
    )

async def send_welcome_email(email: str, user_name: str) -> bool:
    """Send welcome email after verification"""
    context = {
        'user_name': user_name,
    }
    
    return await send_email(
        to_email=email,
        subject="Welcome to Our Learning Platform!",
        template_name="welcome_email",
        context=context
    )