"""
CyberVerse Enterprise Configuration — Professional Edition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Centralized, validated, and environment-aware settings management.
Features:
    - Pydantic Settings v2 with .env + environment variable override
    - Computed fields for derived URLs (async DB URL, public API URL)
    - Field validators for security invariants (key strength, CORS safety)
    - Environment-specific presets (development / staging / production / testing)
    - Secrets masking in __repr__ / logging
    - LRU cached singleton via get_settings()
    - Explicit defaults documented per section for operability

A professional coder structures config as a self-documenting contract
between code and infrastructure. Every value is typed, validated,
and grouped by domain so DevOps can reason about it without reading
application code.
"""

from __future__ import annotations

import os
import warnings
from functools import lru_cache
from typing import Any, Literal

from pydantic import (
    Field,
    PostgresDsn,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENV = Literal["development", "staging", "production", "testing"]


def _env_file_candidates() -> list[str]:
    """Return .env file candidates in priority order."""
    # .env.local overrides .env — standard 12-factor local dev pattern
    return [".env.local", ".env", "backend/.env"]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """
    Application-wide settings.
    Loaded from environment variables and optional .env file(s).
    All secrets should be injected via env vars in production (Vault / SOPS).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_nested_delimiter="__",
        secrets_dir=None,
    )

    # -------------------------------------------------------------------
    # Core Application
    # -------------------------------------------------------------------
    APP_NAME: str = Field(default="CyberVerse API", description="Human-readable service name")
    APP_VERSION: str = Field(default="2.1.0-pro", description="Semantic version exposed at /version")
    APP_DESCRIPTION: str = Field(default="Educational Cybersecurity Simulation Platform — Enterprise Edition")
    ENVIRONMENT: ENV = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=False, description="Enable debug mode (verbose errors, auto-reload)")
    SECRET_KEY: SecretStr = Field(default=SecretStr("change-me-please-32-chars-minimum-secret-key!!"), description="Master secret for signing (32+ chars)")
    API_V1_PREFIX: str = Field(default="/api/v1")
    PUBLIC_API_URL: str | None = Field(default=None, description="Public base URL, e.g. https://api.cyberverse.io")
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend origin for CORS & redirect validation")
    ALLOWED_HOSTS: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"], description="Trusted hosts for Host header validation")

    # -------------------------------------------------------------------
    # Database (PostgreSQL + SQLAlchemy async)
    # -------------------------------------------------------------------
    DATABASE_URL: PostgresDsn | str = Field(default="postgresql://cyberverse:cyberverse@localhost:5432/cyberverse", description="Primary Postgres DSN (sync)")
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100, description="SQLAlchemy pool_size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, ge=0, le=100)
    DATABASE_POOL_TIMEOUT: int = Field(default=15, ge=1, le=120)
    DATABASE_POOL_RECYCLE: int = Field(default=1800, ge=300, le=7200, description="Recycle connections after N seconds")
    DATABASE_POOL_PRE_PING: bool = Field(default=True)
    DATABASE_ECHO: bool = Field(default=False, description="Log all SQL statements (noisy)")
    DATABASE_STATEMENT_TIMEOUT_MS: int = Field(default=5000, ge=1000, le=60000)
    DATABASE_CONNECT_ARGS: dict = Field(default_factory=lambda: {"command_timeout": 10, "server_settings": {"jit": "off", "application_name": "cyberverse-api"}})

    # Read replica (optional)
    DATABASE_REPLICA_URL: PostgresDsn | str | None = Field(default=None)

    # -------------------------------------------------------------------
    # Redis & Caching
    # -------------------------------------------------------------------
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=5, le=500)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1, le=30)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=3, ge=1, le=30)
    REDIS_RETRY_ON_TIMEOUT: bool = Field(default=True)
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(default=30)
    CACHE_DEFAULT_TTL_SECONDS: int = Field(default=300, ge=60, le=86400)
    CACHE_PREFIX: str = Field(default="cyberverse:")

    # -------------------------------------------------------------------
    # Celery (Async Task Queue)
    # -------------------------------------------------------------------
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_SERIALIZER: str = Field(default="json")
    CELERY_RESULT_SERIALIZER: str = Field(default="json")
    CELERY_ACCEPT_CONTENT: list[str] = Field(default_factory=lambda: ["json"])
    CELERY_TIMEZONE: str = Field(default="UTC")
    CELERY_TASK_TRACK_STARTED: bool = Field(default=True)
    CELERY_TASK_TIME_LIMIT: int = Field(default=300, ge=30, le=3600)
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=270)
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = Field(default=1, ge=1, le=8)
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = Field(default=1000, ge=100, le=10000)
    CELERY_BEAT_SCHEDULE_FILENAME: str = Field(default="celerybeat-schedule")

    # -------------------------------------------------------------------
    # Authentication & Security
    # -------------------------------------------------------------------
    JWT_SECRET_KEY: SecretStr = Field(default=SecretStr("change-me-please-32-chars-minimum-jwt-secret!!"))
    JWT_ALGORITHM: str = Field(default="HS256", pattern=r"^(HS256|HS384|HS512|RS256|RS512)$")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, ge=1, le=90)
    JWT_ISSUER: str = Field(default="cyberverse")
    JWT_AUDIENCE: str = Field(default="cyberverse-api")
    JWT_LEEWAY_SECONDS: int = Field(default=10, ge=0, le=60)

    BCRYPT_ROUNDS: int = Field(default=12, ge=10, le=16)
    BCRYPT_PREFIX: str = Field(default="2b")
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=8, le=32)
    PASSWORD_REQUIRE_UPPER: bool = Field(default=True)
    PASSWORD_REQUIRE_NUMBER: bool = Field(default=True)
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=False)

    # Account lockout
    ACCOUNT_LOCKOUT_MAX_ATTEMPTS: int = Field(default=5, ge=3, le=20)
    ACCOUNT_LOCKOUT_WINDOW_MINUTES: int = Field(default=15, ge=5, le=120)
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = Field(default=30, ge=5, le=1440)

    # 2FA / TOTP
    TOTP_ISSUER: str = Field(default="CyberVerse")
    TOTP_DIGITS: int = Field(default=6, ge=6, le=8)
    TOTP_PERIOD: int = Field(default=30, ge=15, le=60)
    TOTP_BACKUP_CODES_COUNT: int = Field(default=8, ge=4, le=16)

    # Session
    SESSION_ABSOLUTE_TIMEOUT_DAYS: int = Field(default=7, ge=1, le=30)
    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=60, ge=10, le=1440)
    SESSION_MAX_PER_USER: int = Field(default=5, ge=1, le=20)

    # OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: SecretStr | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: SecretStr | None = None
    OAUTH_STATE_TTL_MINUTES: int = Field(default=10, ge=5, le=30)

    # Supabase (optional Postgres + Auth provider)
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: SecretStr | None = None
    SUPABASE_JWT_SECRET: SecretStr | None = None
    SUPABASE_STORAGE_BUCKET: str = Field(default="cyberverse-assets")

    # -------------------------------------------------------------------
    # CORS & HTTP
    # -------------------------------------------------------------------
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"])
    CORS_EXPOSE_HEADERS: list[str] = Field(default_factory=lambda: ["X-Request-ID", "X-Response-Time-ms"])
    TRUSTED_PROXIES: list[str] = Field(default_factory=list)

    # Security headers
    HSTS_MAX_AGE: int = Field(default=31536000)
    CSP_REPORT_ONLY: bool = Field(default=False)

    # -------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=10, le=10000)
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=10, le=3600)
    RATE_LIMIT_LOGIN_REQUESTS: int = Field(default=5, ge=3, le=50)
    RATE_LIMIT_LOGIN_WINDOW: int = Field(default=300, ge=60, le=3600)
    RATE_LIMIT_REGISTER_REQUESTS: int = Field(default=3, ge=1, le=20)
    RATE_LIMIT_REGISTER_WINDOW: int = Field(default=3600, ge=600, le=86400)
    RATE_LIMIT_AI_REQUESTS: int = Field(default=10, ge=5, le=100)
    RATE_LIMIT_AI_WINDOW: int = Field(default=60, ge=30, le=600)
    RATE_LIMIT_ENABLED: bool = Field(default=True)

    # -------------------------------------------------------------------
    # Email (SendGrid + fallback)
    # -------------------------------------------------------------------
    SENDGRID_API_KEY: SecretStr | None = None
    SENDGRID_FROM_EMAIL: str = Field(default="noreply@cyberverse.io")
    SENDGRID_FROM_NAME: str = Field(default="CyberVerse")
    SENDGRID_TEMPLATE_VERIFICATION: str | None = None
    SENDGRID_TEMPLATE_RESET: str | None = None
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = Field(default=24, ge=1, le=72)
    PASSWORD_RESET_EXPIRE_HOURS: int = Field(default=1, ge=1, le=24)
    EMAIL_BACKEND: Literal["sendgrid", "console", "dummy"] = Field(default="console")

    # -------------------------------------------------------------------
    # File Upload & Media
    # -------------------------------------------------------------------
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    MAX_VIDEO_FILE_SIZE: int = Field(default=500 * 1024 * 1024)
    ALLOWED_FILE_TYPES: list[str] = Field(default_factory=lambda: ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"])
    ALLOWED_VIDEO_TYPES: list[str] = Field(default_factory=lambda: ["video/mp4", "video/webm", "video/ogg"])
    UPLOAD_DIR: str = Field(default="uploads")
    MEDIA_BASE_URL: str | None = None
    SIGNED_URL_EXPIRE_SECONDS: int = Field(default=3600, ge=300, le=86400)
    THUMBNAIL_WIDTH: int = Field(default=640)
    THUMBNAIL_HEIGHT: int = Field(default=360)

    # -------------------------------------------------------------------
    # Payments (Razorpay)
    # -------------------------------------------------------------------
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: SecretStr | None = None
    RAZORPAY_WEBHOOK_SECRET: SecretStr | None = None
    RAZORPAY_CURRENCY: str = Field(default="INR")
    BILLING_TRIAL_DAYS: int = Field(default=7, ge=0, le=30)

    # -------------------------------------------------------------------
    # AI Services
    # -------------------------------------------------------------------
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = Field(default=4096, ge=256, le=16000)
    OPENAI_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    OPENAI_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    GEMINI_API_KEY: SecretStr | None = None
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash")

    OPENROUTER_API_KEY: SecretStr | None = None
    OPENROUTER_MODEL: str = Field(default="openrouter/auto")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")
    OPENROUTER_MAX_TOKENS: int = Field(default=1000, ge=256, le=8000)
    OPENROUTER_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    OPENROUTER_TIMEOUT_SECONDS: int = Field(default=90, ge=10, le=180)
    OPENROUTER_SITE_URL: str | None = None
    OPENROUTER_APP_NAME: str | None = None
    AI_CHAT_HISTORY_LIMIT: int = Field(default=20, ge=5, le=100)
    AI_CHAT_RATE_LIMIT_PER_MINUTE: int = Field(default=10, ge=5, le=100)
    AI_CONTENT_FILTER_ENABLED: bool = Field(default=True)

    # -------------------------------------------------------------------
    # Logging & Monitoring
    # -------------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    LOG_FORMAT: Literal["json", "console"] = Field(default="json")
    LOG_FILE: str | None = Field(default=None)
    LOG_ROTATION_MAX_MB: int = Field(default=50, ge=10, le=500)
    LOG_RETENTION_DAYS: int = Field(default=14, ge=1, le=90)
    ENABLE_ACCESS_LOG: bool = Field(default=True)

    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, ge=0.0, le=1.0)
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(default=0.1, ge=0.0, le=1.0)
    SENTRY_ENVIRONMENT: str | None = None

    PROMETHEUS_ENABLED: bool = Field(default=False)
    PROMETHEUS_PORT: int = Field(default=9090, ge=1024, le=65535)

    # -------------------------------------------------------------------
    # Pagination & Limits
    # -------------------------------------------------------------------
    DEFAULT_PAGE_SIZE: int = Field(default=20, ge=5, le=50)
    MAX_PAGE_SIZE: int = Field(default=100, ge=20, le=200)
    MAX_SEARCH_RESULTS: int = Field(default=500)
    MAX_BULK_OPERATION_SIZE: int = Field(default=100)

    # -------------------------------------------------------------------
    # Game & Labs
    # -------------------------------------------------------------------
    GAME_WEBSOCKET_URL: str | None = None
    GAME_MAX_PLAYERS_PER_LOBBY: int = Field(default=10, ge=2, le=50)
    GAME_MAX_SESSIONS_PER_USER: int = Field(default=3, ge=1, le=10)
    GAME_SESSION_TTL_HOURS: int = Field(default=24, ge=1, le=72)
    LABS_MAX_EVIDENCE_PER_SESSION: int = Field(default=50, ge=10, le=200)
    LABS_MAX_NOTES_PER_SESSION: int = Field(default=30, ge=10, le=100)
    LABS_ENABLE_AI_MENTOR: bool = Field(default=True)

    # -------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------
    FEATURE_REGISTRATION_ENABLED: bool = Field(default=True)
    FEATURE_GOOGLE_AUTH_ENABLED: bool = Field(default=True)
    FEATURE_2FA_REQUIRED: bool = Field(default=False)
    FEATURE_PREMIUM_ENABLED: bool = Field(default=True)
    FEATURE_LABS_ENABLED: bool = Field(default=True)
    FEATURE_GAME_ENABLED: bool = Field(default=True)
    FEATURE_AI_MENTOR_ENABLED: bool = Field(default=True)
    FEATURE_MAINTENANCE_MODE: bool = Field(default=False)
    FEATURE_MAINTENANCE_MESSAGE: str = Field(default="CyberVerse is under maintenance. We'll be back shortly.")

    # -------------------------------------------------------------------
    # Computed & Validation
    # -------------------------------------------------------------------

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_async(self) -> str:
        """ASGI async URL derived from sync URL."""
        url = str(self.DATABASE_URL)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        url = str(self.DATABASE_URL)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @field_validator("SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def _validate_secret_strength(cls, v: SecretStr) -> SecretStr:
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("Secret must be at least 32 characters")
        if secret.startswith("change-me"):
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("Default secret not allowed in production")
            warnings.warn("Using default secret — not safe for production!", UserWarning, stacklevel=2)
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _validate_cors(cls, v: list[str]) -> list[str]:
        for origin in v:
            if origin == "*":
                raise ValueError("Wildcard CORS origin not allowed — specify explicit origins")
        return v

    @field_validator("DATABASE_POOL_SIZE")
    @classmethod
    def _validate_pool(cls, v: int) -> int:
        if v > 30:
            warnings.warn(f"DATABASE_POOL_SIZE={v} is high — ensure DB max_connections allows it", UserWarning, stacklevel=2)
        return v

    @model_validator(mode="after")
    def _validate_environment_consistency(self) -> Settings:
        if self.is_production:
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if self.LOG_LEVEL == "DEBUG":
                warnings.warn("LOG_LEVEL=DEBUG in production is verbose", UserWarning, stacklevel=2)
            if self.ENVIRONMENT == "production" and not self.SENTRY_DSN:
                warnings.warn("SENTRY_DSN not set in production — observability degraded", UserWarning, stacklevel=2)
        if self.is_testing:
            # Override to in-memory / dummy services for fast tests
            object.__setattr__(self, "EMAIL_BACKEND", "dummy")
            object.__setattr__(self, "RATE_LIMIT_ENABLED", False)
        return self

    def model_dump_masked(self) -> dict[str, Any]:
        """Dump settings with secrets masked for logging."""
        data = self.model_dump()
        for k in list(data.keys()):
            if "SECRET" in k or "KEY" in k or "PASSWORD" in k:
                if data[k]:
                    data[k] = "***masked***"
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached singleton accessor.
    Uses lru_cache so repeated imports don't re-parse .env.
    Call get_settings.cache_clear() in tests to force re-read.
    """
    return Settings()


# Eager singleton for convenience (import { settings } from app.core.config)
settings: Settings = get_settings()
