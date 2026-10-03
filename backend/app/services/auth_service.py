from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_code,
    hash_password,
    verify_backup_code,
    verify_password,
    verify_token_type,
)
from app.models.session import LoginHistory, Session
from app.models.user import AuthProvider, User, UserRole, UserStatus
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest, request_meta: dict) -> dict:
        if data.password != data.confirm_password:
            raise ConflictError("Passwords do not match")

        existing = await db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise ConflictError("Email already registered")

        from app.models.user import Profile
        existing_profile = await db.execute(select(Profile).where(Profile.username == data.username))
        if existing_profile.scalar_one_or_none():
            raise ConflictError("Username already taken")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.STUDENT,
            status=UserStatus.PENDING,
            provider=AuthProvider.EMAIL,
            meta_data=request_meta,
        )
        db.add(user)
        await db.flush()

        from app.models.progress import PlayerProgress
        from app.models.user import Profile

        profile = Profile(
            user_id=user.id,
            username=data.username,
        )
        db.add(profile)

        progress = PlayerProgress(user_id=user.id)
        db.add(progress)

        await db.commit()
        await db.refresh(user)

        tokens = await AuthService._issue_tokens(db, user, request_meta)

        return {"user": user, **tokens}

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest, request_meta: dict) -> dict:
        result = await db.execute(select(User).where(User.email == data.email.lower()))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            await AuthService._record_login(
                db, None, success=False, method="email", reason="invalid_credentials", meta=request_meta
            )
            raise AuthenticationError("Invalid email or password")

        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise AccountLockedError("Account temporarily locked. Try again later.")

        if not verify_password(data.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= AuthService.MAX_FAILED_LOGINS:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=AuthService.LOCKOUT_MINUTES
                )
            await db.commit()
            await AuthService._record_login(
                db, user.id, success=False, method="email", reason="wrong_password", meta=request_meta
            )
            raise AuthenticationError("Invalid email or password")

        if user.totp_secret and not data.totp_code:
            raise AuthenticationError("TOTP code required")

        if user.totp_secret and data.totp_code:
            from app.core.security import verify_totp
            if not verify_totp(user.totp_secret, data.totp_code):
                raise AuthenticationError("Invalid TOTP code")

        if user.totp_secret and data.backup_code:
            matched = False
            for i, code in enumerate(user.backup_codes):
                if verify_backup_code(data.backup_code, code):
                    matched = True
                    user.backup_codes.pop(i)
                    break
            if not matched:
                raise AuthenticationError("Invalid backup code")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(UTC)
        await db.commit()
        await db.refresh(user)

        await AuthService._record_login(
            db, user.id, success=True, method="email", meta=request_meta
        )

        tokens = await AuthService._issue_tokens(db, user, request_meta)

        return {"user": user, **tokens}

    @staticmethod
    async def google_login(db: AsyncSession, email: str, full_name: str, avatar_url: str | None, request_meta: dict) -> dict:
        email = email.lower()
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        from app.models.progress import PlayerProgress
        from app.models.user import Profile

        if not user:
            # Create a new user since they don't exist
            user = User(
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
                role=UserRole.STUDENT,
                status=UserStatus.ACTIVE,
                is_verified=True,  # Google emails are verified
                provider=AuthProvider.GOOGLE,
                meta_data=request_meta,
            )
            db.add(user)
            await db.flush()

            base_username = email.split("@")[0]
            # Ensure unique username
            unique_username = base_username
            counter = 1
            while True:
                existing_profile = await db.execute(select(Profile).where(Profile.username == unique_username))
                if not existing_profile.scalar_one_or_none():
                    break
                unique_username = f"{base_username}{counter}"
                counter += 1

            db.add(Profile(user_id=user.id, username=unique_username, avatar_url=avatar_url))
            db.add(PlayerProgress(user_id=user.id))

            await db.commit()
            await db.refresh(user)
        else:
            if user.locked_until and user.locked_until > datetime.now(UTC):
                raise AccountLockedError("Account temporarily locked. Try again later.")
            # Update provider if they previously signed up with email
            if user.provider != AuthProvider.GOOGLE:
                user.provider = AuthProvider.GOOGLE
                user.is_verified = True

            # Sync avatar if it changed or wasn't set
            if avatar_url and user.avatar_url != avatar_url:
                user.avatar_url = avatar_url
                # We also need to update the profile avatar if it exists
                profile = await db.execute(select(Profile).where(Profile.user_id == user.id))
                profile = profile.scalar_one_or_none()
                if profile:
                    profile.avatar_url = avatar_url

            await db.commit()

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(UTC)
        await db.commit()
        await db.refresh(user)

        await AuthService._record_login(
            db, user.id, success=True, method="google", meta=request_meta
        )

        tokens = await AuthService._issue_tokens(db, user, request_meta)
        return {"user": user, **tokens}

    @staticmethod
    async def refresh(db: AsyncSession, refresh_token: str, request_meta: dict) -> dict:
        try:
            payload = decode_token(refresh_token)
            if not verify_token_type(payload, "refresh"):
                raise AuthenticationError("Invalid refresh token")
            user_id = UUID(payload["sub"])
        except Exception:
            raise AuthenticationError("Invalid refresh token")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        tokens = await AuthService._issue_tokens(db, user, request_meta)
        return {"user": user, **tokens}

    @staticmethod
    async def logout(db: AsyncSession, token: str) -> None:
        await db.execute(
            update(Session)
            .where(Session.token == token, Session.is_revoked.is_(False))
            .values(is_revoked=True, revoked_at=datetime.now(UTC), revoked_by="user")
        )
        await db.commit()

    @staticmethod
    async def revoke_session(db: AsyncSession, user_id: UUID, session_id: UUID) -> None:
        result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Session not found")
        session.is_revoked = True
        session.revoked_at = datetime.now(UTC)
        session.revoked_by = "user"
        await db.commit()

    @staticmethod
    async def list_sessions(db: AsyncSession, user_id: UUID) -> list:
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id, Session.is_revoked.is_(False))
            .order_by(Session.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def setup_2fa(db: AsyncSession, user_id: UUID) -> dict:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        from app.core.security import generate_qr_code, get_totp_uri

        secret = generate_totp_secret()
        backup_codes = generate_backup_codes()
        user.totp_secret = secret
        user.backup_codes = [hash_backup_code(c) for c in backup_codes]
        await db.commit()

        uri = get_totp_uri(secret, user.email)
        qr = generate_qr_code(uri)

        return {
            "secret": secret,
            "qr_code": qr,
            "backup_codes": backup_codes,
            "provisioning_uri": uri,
        }

    @staticmethod
    async def _issue_tokens(db: AsyncSession, user: User, request_meta: dict) -> dict:
        now = datetime.now(UTC)
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        session = Session(
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=request_meta.get("ip_address"),
            user_agent=request_meta.get("user_agent"),
            location=request_meta.get("location"),
            device_info=request_meta.get("device_info", {}),
            expires_at=now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_expires_at=now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    @staticmethod
    async def _record_login(
        db: AsyncSession,
        user_id: UUID | None,
        success: bool,
        method: str,
        reason: str | None = None,
        meta: dict | None = None,
    ) -> None:
        meta = meta or {}
        try:
            db.add(
                LoginHistory(
                    user_id=user_id,
                    success=success,
                    method=method,
                    failure_reason=reason,
                    ip_address=meta.get("ip_address"),
                    user_agent=meta.get("user_agent"),
                    location=meta.get("location"),
                )
            )
            await db.commit()
        except Exception:
            await db.rollback()
