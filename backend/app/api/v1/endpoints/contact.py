"""Public contact form endpoint (pre-login visitors cannot open tickets).

Rate-limited per IP via Redis, honeypot-protected against naive bots, and
delivered through the same graceful SendGrid task pattern as verification
emails: when SendGrid is unconfigured the request still succeeds and the
message is logged instead of leaking infrastructure details to the caller.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.core.cache import CacheService
from app.core.config import settings
from app.schemas.base import APIResponse, MessageResponse

router = APIRouter()
logger = logging.getLogger("cyberverse.contact")

_RATE_LIMIT_PER_HOUR = 5


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    # Honeypot: hidden input on the form. Humans never fill it; bots do.
    website: str = Field(default="", max_length=0)


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=202,
    summary="Submit the public contact form",
)
async def submit_contact(payload: ContactRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    try:
        used = await CacheService(prefix="contact").increment(f"rate:{ip}", amount=1, ttl=3600)
    except Exception:
        # Cache outage must not block legitimate contact; proceed unthrottled.
        used = 1
    if used > _RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many messages from this address. Please try again later.",
        )

    from app.tasks import dispatch_email, send_contact_notification  # noqa: PLC0415

    dispatch_email(
        send_contact_notification,
        payload.name,
        payload.email,
        payload.subject,
        payload.message,
    )
    logger.info(
        "contact_submission",
        extra={"subject": payload.subject, "source_ip": ip},
    )
    return MessageResponse(
        message="Thanks — your message is on its way. We usually reply within one business day."
    )
