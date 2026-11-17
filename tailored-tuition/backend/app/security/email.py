"""Outgoing email: verification and password-reset links.

`console` (development) logs the message instead of sending it. `smtp` sends
via STARTTLS. Sending runs in a FastAPI background task so a slow mail server
never delays the response.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import Settings

log = logging.getLogger(__name__)


def send_email(settings: Settings, to: str, subject: str, body: str) -> None:
    if settings.email_backend != "smtp":
        log.info("[console email] To: %s | Subject: %s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException):
        # Never log the body: it contains a live login link.
        log.exception("Sending email to %s failed", to)


def verification_email(name: str, link: str) -> tuple[str, str]:
    return (
        "Confirm your email for Tailored Tuition",
        f"Hi {name},\n\nPlease confirm your email address by opening this link (valid for 48 hours):\n\n{link}\n\n"
        "If you didn't create an account, you can ignore this email.\n",
    )


def reset_email(name: str, link: str) -> tuple[str, str]:
    return (
        "Reset your Tailored Tuition password",
        f"Hi {name},\n\nOpen this link to choose a new password (valid for 1 hour):\n\n{link}\n\n"
        "If you didn't ask for this, you can ignore this email; your password hasn't changed.\n",
    )
