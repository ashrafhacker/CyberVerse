import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def dispatch_email(task, *args, **kwargs):
    """Dispatch a Celery email task without crashing the request.

    - Testing environment: skipped entirely (fast tests).
    - Broker unavailable / task failure: logged, request continues
      (email is best-effort, never a blocker).
    """
    from app.core.config import settings

    if settings.ENVIRONMENT == "testing":
        logger.info("email_dispatch_skipped", extra={"task": task.name})
        return None
    try:
        return task.delay(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("email_dispatch_failed", extra={"task": task.name, "error": str(exc)})
        return None


@shared_task(name="app.tasks.email_tasks.send_verification_email")
def send_verification_email(email: str, token: str) -> dict:
    """Send email verification email via SendGrid (or log in dev)."""
    try:
        from app.core.config import settings
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=email,
            subject="Verify your CyberVerse account",
            html_content=(
                f"<h2>Welcome to CyberVerse!</h2>"
                f"<p>Click the link below to verify your email address:</p>"
                f"<p><a href='https://cyberverse.io/verify-email?token={token}'>Verify Email</a></p>"
            ),
        )
        response = sg.send(message)
        return {"email": email, "status_code": response.status_code}
    except Exception as exc:  # noqa: BLE001
        import structlog
        structlog.get_logger(__name__).warning("email_skipped", email=email, error=str(exc))
        return {"email": email, "status": "skipped", "error": str(exc)}


@shared_task(name="app.tasks.email_tasks.send_password_reset_email")
def send_password_reset_email(email: str, token: str) -> dict:
    try:
        from app.core.config import settings
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=email,
            subject="Reset your CyberVerse password",
            html_content=(
                f"<p>Click the link below to reset your password:</p>"
                f"<p><a href='https://cyberverse.io/reset-password?token={token}'>Reset Password</a></p>"
                f"<p>This link expires in 1 hour.</p>"
            ),
        )
        response = sg.send(message)
        return {"email": email, "status_code": response.status_code}
    except Exception as exc:  # noqa: BLE001
        import structlog
        structlog.get_logger(__name__).warning("email_skipped", email=email, error=str(exc))
        return {"email": email, "status": "skipped", "error": str(exc)}