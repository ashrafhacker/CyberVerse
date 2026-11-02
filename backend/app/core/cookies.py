"""HttpOnly session-cookie helpers for cookie-based JWT transport.

The access and refresh JWTs are delivered as HttpOnly cookies so browser
JavaScript can never read them (XSS cannot exfiltrate a session). The refresh
cookie is additionally scoped to the auth routes only, and a separate
non-HttpOnly CSRF cookie backs the double-submit check on state-changing
requests.

Bearer headers remain accepted by the API for non-browser clients
(CLI, mobile, WebSocket ``?token=``), but the web client no longer receives
tokens in response bodies unless it explicitly opts in.
"""

import secrets
from urllib.parse import urlsplit

from starlette.responses import Response

from app.core.config import settings

ACCESS_COOKIE = "cv_access"
REFRESH_COOKIE = "cv_refresh"
CSRF_COOKIE = "cv_csrf"

CSRF_TOKEN_BYTES = 32


def cookie_secure() -> bool:
    """Resolve the Secure flag: explicit setting, else production-only."""
    if settings.COOKIE_SECURE is not None:
        return settings.COOKIE_SECURE
    return settings.is_production


def access_cookie_path() -> str:
    """Access cookie: every API route needs it (incl. media streaming)."""
    return settings.API_V1_PREFIX


def refresh_cookie_path() -> str:
    """Refresh cookie: only the auth sub-routes may read it."""
    return f"{settings.API_V1_PREFIX}/auth"


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(CSRF_TOKEN_BYTES)


def set_csrf_cookie(response: Response, token: str) -> None:
    """CSRF cookie must be readable by frontend JS — not HttpOnly, Path=/."""
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
        domain=settings.COOKIE_DOMAIN,
        secure=cookie_secure(),
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    """Set access/refresh HttpOnly cookies and a fresh CSRF cookie.

    Returns the CSRF token so callers can log or return it when needed.
    """
    secure = cookie_secure()
    samesite = settings.COOKIE_SAMESITE
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=access_cookie_path(),
        domain=settings.COOKIE_DOMAIN,
        secure=secure,
        httponly=True,
        samesite=samesite,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=refresh_cookie_path(),
        domain=settings.COOKIE_DOMAIN,
        secure=secure,
        httponly=True,
        samesite=samesite,
    )
    csrf_token = issue_csrf_token()
    set_csrf_cookie(response, csrf_token)
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Delete every auth cookie with matching path/domain attributes."""
    secure = cookie_secure()
    samesite = settings.COOKIE_SAMESITE
    response.delete_cookie(
        ACCESS_COOKIE,
        path=access_cookie_path(),
        domain=settings.COOKIE_DOMAIN,
        secure=secure,
        httponly=True,
        samesite=samesite,
    )
    response.delete_cookie(
        REFRESH_COOKIE,
        path=refresh_cookie_path(),
        domain=settings.COOKIE_DOMAIN,
        secure=secure,
        httponly=True,
        samesite=samesite,
    )
    response.delete_cookie(
        CSRF_COOKIE,
        path="/",
        domain=settings.COOKIE_DOMAIN,
        secure=secure,
        httponly=False,
        samesite=samesite,
    )


def _normalise_origin(origin: str) -> str:
    origin = origin.strip().rstrip("/")
    parts = urlsplit(origin)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return origin


def origin_allowed(origin: str) -> bool:
    """True when the Origin/Referer may perform credentialed writes.

    Allowed: configured CORS origins, the frontend origin, and (outside
    production) any localhost/127.0.0.1 origin — mirroring the CORS policy so
    the CSRF check never rejects a request CORS would accept.
    """
    if not origin:
        return False
    candidate = _normalise_origin(origin)
    if candidate in {_normalise_origin(o) for o in settings.CORS_ORIGINS}:
        return True
    if candidate == _normalise_origin(settings.FRONTEND_URL):
        return True
    if not settings.is_production:
        parts = urlsplit(candidate)
        if parts.scheme in ("http", "https") and parts.hostname in ("localhost", "127.0.0.1"):
            return True
    return False


def origin_from_referer(referer: str) -> str | None:
    parts = urlsplit(referer)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return None
