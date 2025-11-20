import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_welcome_email(to_email: str, name: str) -> None:
    """
    Environment variables:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASSWORD
    - SMTP_FROM (optional, defaults to SMTP_USER)
    - SMTP_USE_SSL (optional, 'true' to use SMTP_SSL)
    - SMTP_STARTTLS (optional, 'true' to use STARTTLS)

    If SMTP_HOST is not set, this becomes a no-op (only logs).
    """
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.info("SMTP not configured; skipping welcome email to %s", to_email)
        return

    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
    starttls = os.getenv("SMTP_STARTTLS", "false").lower() == "true"

    subject = "Welcome to Docu-Serve"
    body = f"Thank you {name} for joining Docu-Serve"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from or "noreply@example.com"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
                if smtp_user and smtp_password:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                smtp.ehlo()
                if starttls:
                    smtp.starttls()
                    smtp.ehlo()
                if smtp_user and smtp_password:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
        logger.info("Sent welcome email to %s", to_email)
    except Exception as exc:
        logger.exception("Failed to send welcome email to %s: %s", to_email, exc)
