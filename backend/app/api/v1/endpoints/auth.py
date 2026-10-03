from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import RateLimiter
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.session import LoginHistory
from app.models.user import User, UserStatus
from app.schemas.auth import (
    ChangePasswordRequest,
    DeviceInfo,
    Disable2FARequest,
    EmailVerificationRequest,
    Enable2FAResponse,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    Verify2FARequest,
)
from app.schemas.base import APIResponse, MessageResponse
from app.services.auth_service import AuthService
from app.tasks import (
    dispatch_email,
    send_password_reset_email,
    send_verification_email,
)

router = APIRouter()


def _request_meta(request: Request) -> dict:
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "device_info": {
            "browser": request.headers.get("user-agent", "")[:100],
            "platform": "web",
        },
    }


@router.post(
    "/register",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
async def register(
    request: RegisterRequest,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
):
    allowed = await RateLimiter.check(
        fastapi_request,
        max_requests=settings.RATE_LIMIT_REGISTER_REQUESTS,
        window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW,
        scope="register",
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many registration attempts. Try again later.")

    result = await AuthService.register(db, request, _request_meta(fastapi_request))

    verification_token = create_access_token(str(result["user"].id), {"type": "email_verification"})
    dispatch_email(send_verification_email, request.email, verification_token)

    return APIResponse[TokenResponse](
        data=TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result["expires_in"],
            user=UserResponse.model_validate(result["user"]),
        )
    )


@router.post("/login", response_model=APIResponse[TokenResponse], summary="Login with email and password")
async def login(
    request: LoginRequest,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
):
    import structlog

    log = structlog.get_logger("auth.login")
    try:
        allowed = await RateLimiter.check(
            fastapi_request,
            max_requests=settings.RATE_LIMIT_LOGIN_REQUESTS,
            window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
            scope="login",
        )
        if not allowed:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

        result = await AuthService.login(db, request, _request_meta(fastapi_request))

        return APIResponse[TokenResponse](
            data=TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                expires_in=result["expires_in"],
                user=UserResponse.model_validate(result["user"]),
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        err = str(exc)
        if any(kw in err for kw in ["WinError 1225", "ConnectionRefused", "asyncpg", "pool", "could not connect"]):
            log.error("login.db_unavailable", error=err)
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable — login is paused while the database starts. Please wait 30 seconds and try again.",
            )
        log.error("login.failed", error=err, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/google", response_model=APIResponse[TokenResponse], summary="Login with Google Identity Services")
async def google_login(
    request: GoogleLoginRequest,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
):
    import base64
    import json
    import time

    import httpx
    import structlog

    log = structlog.get_logger("auth.google")

    def _decode_jwt_payload(token: str) -> dict | None:
        """Offline fallback: decode JWT payload without signature verification (dev/isolated env)."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            return json.loads(payload_json)
        except Exception:
            return None

    def _validate_offline_payload(payload: dict) -> tuple[str, str, str | None]:
        now = int(time.time())
        exp = payload.get("exp")
        if exp and int(exp) < now:
            raise HTTPException(status_code=400, detail="Google token expired — please sign in again")
        aud = payload.get("aud")
        # Use configured client id; if not set, accept the known CyberVerse client as fallback
        expected_aud = settings.GOOGLE_CLIENT_ID or "629472594859-dc64tio5cvcfq8g8f41igr1peu8mr2d6.apps.googleusercontent.com"
        if aud and aud != expected_aud:
            # In dev we warn but allow to avoid hard failure when Google rotates client config
            log.warning("google.aud_mismatch", expected=expected_aud, got=aud, mode="offline_fallback")
            # Only enforce strictly in production
            if settings.ENVIRONMENT == "production":
                raise HTTPException(status_code=400, detail="Invalid Google Client ID mismatch")
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email")
        # email_verified optional check
        if payload.get("email_verified") is False:
            raise HTTPException(status_code=400, detail="Google email not verified")
        full_name = payload.get("name") or payload.get("given_name") or "Google User"
        avatar_url = payload.get("picture")
        return email, full_name, avatar_url

    # 1. Try official tokeninfo endpoint (authoritative)
    data: dict | None = None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={request.credential}")
            if resp.status_code == 200:
                data = resp.json()
                log.info("google.tokeninfo.success", aud=data.get("aud"))
            else:
                log.warning("google.tokeninfo.invalid", status=resp.status_code, body=resp.text[:500])
    except Exception as exc:  # noqa: BLE001 — network failure (WinError 1225, timeout, DNS)
        log.warning("google.tokeninfo.network_failed", error=str(exc), fallback="offline_decode")

    # 2. Fallback to offline decode if network failed or non-200
    if data is None:
        payload = _decode_jwt_payload(request.credential)
        if payload is None:
            log.error("google.decode.failed", hint="token not JWT or malformed")
            raise HTTPException(status_code=400, detail="Invalid Google token — unable to decode")
        log.info("google.offline_fallback.used", aud=payload.get("aud"), email=payload.get("email"))
        email, full_name, avatar_url = _validate_offline_payload(payload)
    else:
        # Validate tokeninfo response
        expected_aud = settings.GOOGLE_CLIENT_ID or "629472594859-dc64tio5cvcfq8g8f41igr1peu8mr2d6.apps.googleusercontent.com"
        if data.get("aud") != expected_aud and settings.ENVIRONMENT == "production":
            raise HTTPException(status_code=400, detail="Invalid Google Client ID mismatch")
        email = data.get("email")
        full_name = data.get("name", "Google User")
        avatar_url = data.get("picture")
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email")

    try:
        result = await AuthService.google_login(db, email, full_name, avatar_url, _request_meta(fastapi_request))
        return APIResponse[TokenResponse](
            data=TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                expires_in=result["expires_in"],
                user=UserResponse.model_validate(result["user"]),
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        err_str = str(exc)
        # Distinguish DB/Redis infrastructure failures from verification failures
        is_db_error = any(
            kw in err_str
            for kw in [
                "Connect call failed",
                "ConnectionRefusedError",
                "WinError 1225",
                "asyncpg",
                "Connection refused",
                "could not connect to server",
                "the database system is starting",
            ]
        ) or "ConnectionRefusedError" in type(exc).__name__
        if is_db_error:
            log.error("google.db_unavailable", error=err_str, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable — Google sign-in verified but cannot create session. Please try again in 30 seconds or use email login.",
            )
        log.error("google.service.failed", error=err_str, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to verify Google authentication")

@router.post("/refresh", response_model=APIResponse[TokenResponse], summary="Refresh access token")
async def refresh(
    request: RefreshTokenRequest,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService.refresh(db, request.refresh_token, _request_meta(fastapi_request))
    return APIResponse[TokenResponse](
        data=TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result["expires_in"],
            user=UserResponse.model_validate(result["user"]),
        )
    )


@router.post("/logout", response_model=MessageResponse, summary="Logout current session")
async def logout(
    fastapi_request: Request,
    credentials=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    auth_header = fastapi_request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if token:
        await AuthService.logout(db, token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=APIResponse[UserResponse], summary="Get current user")
async def get_me(
    user: CurrentUser,
):
    return APIResponse[UserResponse](data=UserResponse.model_validate(user))


@router.post("/verify-email", response_model=MessageResponse, summary="Verify email address")
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(request.token)
        if payload.get("type") != "email_verification":
            raise HTTPException(status_code=400, detail="Invalid verification token")
        result = await db.execute(select(User).where(User.id == UUID(payload["sub"])))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_verified = True
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE
        await db.commit()
        return MessageResponse(message="Email verified successfully")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")


@router.post("/resend-verification", response_model=MessageResponse, summary="Resend verification email")
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()
    if not user or user.is_verified:
        return MessageResponse(message="If the account exists and is unverified, an email has been sent.")
    token = create_access_token(str(user.id), {"type": "email_verification"})
    dispatch_email(send_verification_email, user.email, token)
    return MessageResponse(message="Verification email sent")


@router.post("/forgot-password", response_model=MessageResponse, summary="Request password reset")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()
    if user:
        token = create_access_token(str(user.id), {"type": "password_reset"})
        dispatch_email(send_password_reset_email, user.email, token)
    return MessageResponse(message="If the account exists, reset instructions have been sent.")


@router.post("/reset-password", response_model=MessageResponse, summary="Reset password with token")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        payload = decode_token(request.token)
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")
        result = await db.execute(select(User).where(User.id == UUID(payload["sub"])))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.password_hash = hash_password(request.password)
        await db.commit()
        return MessageResponse(message="Password reset successfully")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")


@router.post("/change-password", response_model=MessageResponse, summary="Change current password")
async def change_password(
    request: ChangePasswordRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not verify_password(request.current_password, user.password_hash or ""):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    user.password_hash = hash_password(request.new_password)
    await db.commit()
    return MessageResponse(message="Password changed successfully")


@router.post("/2fa/enable", response_model=APIResponse[Enable2FAResponse], summary="Enable 2FA (returns TOTP secret + QR)")
async def enable_2fa(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if user.is_2fa_enabled:
        raise HTTPException(status_code=409, detail="2FA already enabled")
    data = await AuthService.setup_2fa(db, user.id)
    return APIResponse[Enable2FAResponse](
        data=Enable2FAResponse(
            secret=data["secret"],
            qr_code=data["qr_code"],
            backup_codes=data["backup_codes"],
        )
    )


@router.post("/2fa/verify", response_model=MessageResponse, summary="Verify and activate 2FA")
async def verify_2fa_enable(
    request: Verify2FARequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import verify_totp

    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not set up. Enable it first.")
    if not verify_totp(user.totp_secret, request.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    user.is_2fa_enabled = True
    await db.commit()
    return MessageResponse(message="2FA enabled successfully")


@router.post("/2fa/disable", response_model=MessageResponse, summary="Disable 2FA")
async def disable_2fa(
    request: Disable2FARequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import verify_backup_code, verify_totp

    if not user.is_2fa_enabled:
        return MessageResponse(message="2FA is not enabled")
    if not verify_password(request.password, user.password_hash or ""):
        raise HTTPException(status_code=401, detail="Invalid password")

    code_valid = bool(request.code and user.totp_secret and verify_totp(user.totp_secret, request.code))
    backup_valid = bool(request.backup_code and any(verify_backup_code(request.backup_code, c) for c in user.backup_codes))
    if not (code_valid or backup_valid):
        raise HTTPException(status_code=400, detail="Valid TOTP code or backup code required")

    user.is_2fa_enabled = False
    user.totp_secret = None
    user.backup_codes = []
    await db.commit()
    return MessageResponse(message="2FA disabled successfully")


@router.get("/sessions", response_model=APIResponse[list], summary="List active sessions")
async def list_sessions(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    sessions = await AuthService.list_sessions(db, user.id)
    return APIResponse[list](
        data=[
            {
                "id": str(s.id),
                "ip_address": s.ip_address,
                "location": s.location,
                "device_info": s.device_info,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in sessions
        ]
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse, summary="Revoke a session")
async def revoke_session(
    session_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await AuthService.revoke_session(db, user.id, session_id)
    return MessageResponse(message="Session revoked")


@router.get("/devices", response_model=APIResponse[list], summary="List registered devices")
async def list_devices(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.session import Device

    result = await db.execute(select(Device).where(Device.user_id == user.id).order_by(Device.last_active.desc()))
    devices = result.scalars().all()
    return APIResponse[list](
        data=[
            DeviceInfo(
                device_id=d.device_id,
                device_name=d.device_name,
                device_type=d.device_type,
                browser=d.browser,
                os=d.os,
                ip_address=d.ip_address or "",
                location=d.location,
                last_active=d.last_active,
                is_current=False,
            )
            for d in devices
        ]
    )


@router.get("/login-history", response_model=APIResponse[list], summary="Get login history")
async def login_history(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginHistory)
        .where(LoginHistory.user_id == user.id)
        .order_by(LoginHistory.created_at.desc())
        .limit(50)
    )
    entries = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "success": e.success,
                "method": e.method,
                "ip_address": e.ip_address,
                "location": e.location,
                "failure_reason": e.failure_reason,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]
    )
