from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    GUEST = "guest"
    STUDENT = "student"
    PREMIUM_STUDENT = "premium_student"
    INSTRUCTOR = "instructor"
    MODERATOR = "moderator"
    ADMINISTRATOR = "administrator"
    DEVELOPER = "developer"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str
    full_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    accept_terms: bool = True
    accept_privacy: bool = True
    referral_code: str | None = None

    def passwords_match(self) -> bool:
        return self.password == self.confirm_password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    totp_code: str | None = None
    backup_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    def passwords_match(self) -> bool:
        return self.password == self.confirm_password


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    def passwords_match(self) -> bool:
        return self.new_password == self.confirm_password


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    code: str


class Disable2FARequest(BaseModel):
    password: str
    code: str | None = None
    backup_code: str | None = None


class GoogleLoginRequest(BaseModel):
    credential: str

class OAuthLoginRequest(BaseModel):
    provider: AuthProvider
    code: str
    redirect_uri: str
    state: str | None = None


class DeviceInfo(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    browser: str
    os: str
    ip_address: str
    location: str | None = None
    last_active: datetime
    is_current: bool = False


class SessionResponse(BaseModel):
    id: UUID
    device: DeviceInfo
    created_at: datetime
    expires_at: datetime
    is_current: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    role: UserRole
    status: UserStatus
    is_verified: bool
    is_2fa_enabled: bool
    provider: AuthProvider
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserProfileResponse(UserResponse):
    xp: int = 0
    coins: int = 0
    level: int = 1
    rank: str | None = None
    titles: list[str] = []
    badges: list[str] = []
    statistics: dict = {}
    preferences: dict = {}
