import os
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Notification

logger = logging.getLogger(__name__)

# circuit breaker to prevent spamming smtp server if it's down
_smtp_circuit_breaker = {
    'failures': 0,
    'last_failure_time': None,
    'state': 'closed',  # closed, open, half_open
    'failure_threshold': 5,
    'timeout': 60  # wait a minute before retrying
}

def _check_smtp_circuit():
    """see if we're allowed to send emails right now"""
    cb = _smtp_circuit_breaker
    
    if cb['state'] == 'open':
        # check if enough time passed to try again
        if cb['last_failure_time'] and \
           (datetime.now() - cb['last_failure_time']).total_seconds() > cb['timeout']:
            cb['state'] = 'half_open'
            logger.info("SMTP circuit breaker entering half-open state")
            return True
        return False
    
    return True

def _record_smtp_success():
    """reset circuit breaker after successful send"""
    cb = _smtp_circuit_breaker
    if cb['state'] == 'half_open':
        logger.info("SMTP circuit breaker closing after successful operation")
    cb['failures'] = 0
    cb['state'] = 'closed'
    cb['last_failure_time'] = None

def _record_smtp_failure():
    """track failures and open circuit if needed"""
    cb = _smtp_circuit_breaker
    cb['failures'] += 1
    cb['last_failure_time'] = datetime.now()
    
    # if we hit threshold, stop trying for a bit
    if cb['failures'] >= cb['failure_threshold']:
        if cb['state'] != 'open':
            logger.warning(f"SMTP circuit breaker opened after {cb['failures']} failures")
        cb['state'] = 'open'


def send_welcome_email(to_email: str, name: str) -> None:
    """
    Sends welcome email to new users.
    Needs SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD env vars.
    """
    # check if circuit breaker is blocking us
    if not _check_smtp_circuit():
        logger.warning("SMTP circuit breaker is open; skipping welcome email to %s", to_email)
        return
    
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
        _record_smtp_success()
        
        # log this email in the database
        db = SessionLocal()
        try:
            notification = Notification(
                user_email=to_email,
                notification_type="welcome",
                subject=subject,
                message=body,
                delivered=True
            )
            db.add(notification)
            db.commit()
        except Exception as db_err:
            logger.error(f"Failed to save notification: {db_err}")
        finally:
            db.close()
            
    except Exception as exc:
        logger.exception("Failed to send welcome email to %s: %s", to_email, exc)
        _record_smtp_failure()
        
        # still save to db even if it failed
        db = SessionLocal()
        try:
            notification = Notification(
                user_email=to_email,
                notification_type="welcome",
                subject=subject,
                message=body,
                delivered=False
            )
            db.add(notification)
            db.commit()
        finally:
            db.close()


def send_goodbye_email(to_email: str, name: str) -> None:
    """
    Sends goodbye email when users delete their account.
    Includes link to feedback form.
    """
    # check circuit breaker first
    if not _check_smtp_circuit():
        logger.warning("SMTP circuit breaker is open; skipping goodbye email to %s", to_email)
        return
    
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.info("SMTP not configured; skipping goodbye email to %s", to_email)
        return

    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
    starttls = os.getenv("SMTP_STARTTLS", "false").lower() == "true"

    subject = "We're sorry to see you go"
    body = f"""Hello {name},

We're sorry to see you leave Docu-Serve. Your account has been successfully deleted.

We'd love to hear your feedback to help us improve our service. Please take a moment to fill out this brief survey:

https://forms.cloud.microsoft/e/E5ZhG3hbqS

Thank you for being part of our community.

Kind regards,
The Docu-Serve Team
"""

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
        logger.info("Sent goodbye email to %s", to_email)
        _record_smtp_success()
        
        # save to db
        db = SessionLocal()
        try:
            notification = Notification(
                user_email=to_email,
                notification_type="goodbye",
                subject=subject,
                message=body,
                delivered=True
            )
            db.add(notification)
            db.commit()
        except Exception as db_err:
            logger.error(f"Failed to save notification: {db_err}")
        finally:
            db.close()
            
    except Exception as exc:
        logger.exception("Failed to send goodbye email to %s: %s", to_email, exc)
        _record_smtp_failure()
        
        # Save failed notification
        db = SessionLocal()
        try:
            notification = Notification(
                user_email=to_email,
                notification_type="goodbye",
                subject=subject,
                message=body,
                delivered=False
            )
            db.add(notification)
            db.commit()
        finally:
            db.close()
