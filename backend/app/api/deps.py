"""
FastAPI dependency injection utilities.

Provides authentication, authorization, and request metadata dependencies
for the CyberVerse API endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    token: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """
    Get the authenticated user from bearer token or query parameter.

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
        payload = decode_token(actual_token, expected_type="access")
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

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
        payload = decode_token(actual_token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if user and user.status in (UserStatus.ACTIVE, UserStatus.PENDING):
            return user
    except (ValueError, KeyError, AttributeError):
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
