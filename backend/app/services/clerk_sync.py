"""
Sync Clerk identities into the local ``users`` table.

Clerk is the identity authority; Postgres stays the record authority. On first
sight of a Clerk user (lazy sync from ``get_current_user`` or via the Clerk
webhook) we upsert a local row keyed by ``users.provider_id`` = the Clerk user
id. If a row already exists for the same email (a pre-Clerk account) it is
*linked* — its id, role, XP and all foreign-keyed data are preserved.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk import email_verified, primary_email
from app.models.progress import PlayerProgress
from app.models.user import AuthProvider, Profile, User, UserRole, UserStatus


async def _unique_username(db: AsyncSession, base: str) -> str:
    """Return a username derived from ``base`` that is not already taken."""
    base = (base or "agent").strip() or "agent"
    # Keep within the column limit and strip characters that break usernames.
    base = "".join(ch for ch in base if ch.isalnum() or ch in "_-")[:40] or "agent"
    candidate = base
    counter = 1
    while True:
        existing = await db.execute(select(Profile).where(Profile.username == candidate))
        if not existing.scalar_one_or_none():
            return candidate
        candidate = f"{base}{counter}"
        counter += 1


async def sync_clerk_user(
    db: AsyncSession,
    clerk_user_id: str,
    clerk_user: dict | None = None,
) -> User:
    """Create or update the local user for a Clerk identity and return it.

    Args:
        db: Async DB session.
        clerk_user_id: The Clerk user id (``user_…``).
        clerk_user: Optional pre-fetched Clerk user object; fetched if omitted.

    Returns:
        The upserted, committed ``User``.
    """
    from app.core.clerk import get_clerk_user  # local import to avoid cycles

    if clerk_user is None:
        clerk_user = await get_clerk_user(clerk_user_id)

    email = primary_email(clerk_user)
    full_name = " ".join(
        part for part in (clerk_user.get("first_name"), clerk_user.get("last_name")) if part
    ) or clerk_user.get("username") or (email.split("@")[0] if email else "CyberVerse User")
    avatar_url = clerk_user.get("image_url")
    verified = email_verified(clerk_user)

    # 1) Existing row keyed by this Clerk id?
    result = await db.execute(select(User).where(User.provider_id == clerk_user_id))
    user = result.scalar_one_or_none()

    if user is None and email:
        # 2) Same email registered before Clerk (email/google) → link it.
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    now = datetime.now(UTC)

    if user is None:
        if not email:
            # Clerk can (rarely) have a user with no email — we require one to
            # key the account. Reject rather than create an unusable row.
            raise ValueError("Clerk user has no email address to sync")
        username = await _unique_username(db, email.split("@")[0])
        user = User(
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
            is_verified=verified,
            provider=AuthProvider.CLERK,
            provider_id=clerk_user_id,
        )
        db.add(user)
        await db.flush()
        db.add(Profile(user_id=user.id, username=username, avatar_url=avatar_url))
        db.add(PlayerProgress(user_id=user.id))
    else:
        # Link / update the existing row.
        user.provider = AuthProvider.CLERK
        user.provider_id = clerk_user_id
        if full_name:
            user.full_name = full_name
        if avatar_url:
            user.avatar_url = avatar_url
        if verified:
            user.is_verified = True
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE

    user.last_login = now
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    await db.refresh(user)
    return user
