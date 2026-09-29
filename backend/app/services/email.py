"""Email delivery seam.

Production delivery is deliberately disabled until provider credentials are
configured.  Console mode is safe for local UI/API testing only.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.settings import settings

logger = logging.getLogger(__name__)


def send_student_activation(email: str, token: str, *, reset: bool = False) -> None:
    link = f"{settings.public_app_url}/activate?token={token}"
    if reset:
        link += "&mode=reset"
    if settings.email_delivery_mode == "console":
        logger.warning("LOCAL ONLY activation email to %s: %s", email, link)
        return
    if settings.email_delivery_mode == "disabled":
        logger.warning("Activation email suppressed because delivery is disabled")
        return
    if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.email_from)):
        raise RuntimeError("Production email delivery is missing SMTP settings")
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = email
    message["Subject"] = "Reset your EMC Veritas password" if reset else "Activate your EMC Veritas account"
    message.set_content(
        f"Use this one-time link to {'reset your password' if reset else 'activate your EMC Veritas account'}. "
        f"It expires in 15 minutes:\n\n{link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
        client.starttls()
        client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)
