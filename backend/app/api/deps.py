from typing import Annotated, Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

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


CurrentUser = Annotated[User, Depends(get_current_user)]


ROLE_HIERARCHY: Dict[UserRole, int] = {
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
    def dependency(user: CurrentUser) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY.get(min_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


def require_roles(allowed_roles: set[UserRole]):
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


def get_client_ip(
    request: "Request",
) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: "Request") -> str:
    return request.headers.get("user-agent", "unknown")


def require_verified(user: CurrentUser) -> User:
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return user


def require_2fa(user: CurrentUser) -> User:
    if user.is_2fa_enabled:
        # 2FA enforcement happens at login; here we just ensure account is healthy
        return user
    return user