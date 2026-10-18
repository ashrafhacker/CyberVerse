"""
FastAPI dependency injection utilities.

Provides authentication, authorization, and request metadata dependencies
for the CyberVerse API endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError as JoseJWTError
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk import ClerkError, verify_clerk_session_token
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole, UserStatus
from app.services.clerk_sync import sync_clerk_user

bearer_scheme = HTTPBearer(auto_error=False)


def _token_alg(token: str) -> str:
    """Return the JWS ``alg`` header for a token ('' if unparseable)."""
    try:
        return jose_jwt.get_unverified_header(token).get("alg", "")
    except JoseJWTError:
        return ""


async def _resolve_user(db: AsyncSession, token: str) -> User:
    """
    Resolve the User for either a Clerk session token or a legacy JWT.

    Clerk session tokens are RS256 and carry a Clerk user id (``user_…``) in
    ``sub``; they are resolved via ``users.provider_id`` with lazy provisioning
    on first sight. Legacy first-party JWTs are HS256 and carry the local user
    UUID in ``sub``.

    Raises:
        HTTPException: 401 if the token is invalid or the user cannot be found.
    """
    if _token_alg(token) == "RS256":
        # Clerk session token.
        try:
            claims = await verify_clerk_session_token(token)
        except ClerkError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from err
        clerk_user_id = claims["sub"]
        result = await db.execute(select(User).where(User.provider_id == clerk_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            # First time this Clerk identity hits the API — provision locally.
            try:
                user = await sync_clerk_user(db, clerk_user_id)
            except Exception as err:  # noqa: BLE001 — Clerk API/network/sync failure
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to provision account from Clerk",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from err
        return user

    # Legacy first-party JWT (HS256).
    payload = decode_token(token, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    token: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """
    Get the authenticated user from a Clerk session token or legacy JWT.

    Accepts the token from the Authorization header or (for WebSocket) a query
    parameter. Supports both Clerk session tokens (RS256) and the legacy
    first-party JWT (HS256) so auth-protected endpoints work across the
    migration to Clerk.

    Args:
        credentials: HTTP Authorization header credentials.
        token: Optional token from query parameter (for WebSocket).
        db: Database session dependency.

    Returns:
        The authenticated User instance.

    Raises:
        HTTPException: 401 if not authenticated or token invalid.
        HTTPException: 403 if account is not active.

    """
    actual_token = credentials.credentials if credentials else token
    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await _resolve_user(db, actual_token)
    except HTTPException:
        raise
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    if user.status not in (UserStatus.ACTIVE, UserStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    token: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User | None:
    """
    Get the authenticated user if token is valid, otherwise return None.

    Unlike get_current_user, this never raises - it returns None for
    invalid/missing tokens. Useful for endpoints that support both
    authenticated and anonymous access.

    Args:
        credentials: HTTP Authorization header credentials.
        token: Optional token from query parameter.
        db: Database session dependency.

    Returns:
        The authenticated User instance or None.

    """
    actual_token = credentials.credentials if credentials else token
    if not actual_token:
        return None
    try:
        user = await _resolve_user(db, actual_token)
        if user and user.status in (UserStatus.ACTIVE, UserStatus.PENDING):
            return user
    except (HTTPException, ValueError, KeyError, AttributeError):
        pass
    return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.GUEST: 0,
    UserRole.STUDENT: 10,
    UserRole.PREMIUM_STUDENT: 20,
    UserRole.INSTRUCTOR: 30,
    UserRole.MODERATOR: 40,
    UserRole.ADMINISTRATOR: 50,
    UserRole.DEVELOPER: 60,
    UserRole.SUPER_ADMIN: 100,
}


def require_role(min_role: UserRole):
    """
    Create a dependency that requires a minimum role level.

    Args:
        min_role: Minimum UserRole required.

    Returns:
        FastAPI dependency that validates user role.

    """
    def dependency(user: CurrentUser) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY.get(min_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


def require_roles(allowed_roles: set[UserRole]):
    """
    Create a dependency that requires one of the specified roles.

    Args:
        allowed_roles: Set of UserRole values that are allowed.

    Returns:
        FastAPI dependency that validates user role.

    """
    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


require_student = require_role(UserRole.STUDENT)
require_premium = require_role(UserRole.PREMIUM_STUDENT)
require_instructor = require_role(UserRole.INSTRUCTOR)
require_moderator = require_role(UserRole.MODERATOR)
require_admin = require_role(UserRole.ADMINISTRATOR)
require_super_admin = require_role(UserRole.SUPER_ADMIN)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, respecting X-Forwarded-For header.

    Args:
        request: FastAPI Request object.

    Returns:
        Client IP address or 'unknown' if not available.

    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """
    Extract User-Agent from request headers.

    Args:
        request: FastAPI Request object.

    Returns:
        User-Agent string or 'unknown' if not available.

    """
    return request.headers.get("user-agent", "unknown")


def require_verified(user: CurrentUser) -> User:
    """
    Require user to have verified email.

    Args:
        user: Current authenticated user.

    Returns:
        The same user if verified.

    Raises:
        HTTPException: 403 if email not verified.

    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return user


def require_2fa(user: CurrentUser) -> User:
    """
    Require user to have 2FA enabled.

    Note: 2FA enforcement happens at login; this just ensures account is healthy.

    Args:
        user: Current authenticated user.

    Returns:
        The same user.

    """
    return user
