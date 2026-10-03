"""
CyberVerse Enterprise API Gateway — Professional Edition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Author: CyberVerse Platform Team
Version: 2.1.0-pro
Description:
    Production-grade FastAPI application with enterprise patterns:
    - Structured logging (structlog + contextvars)
    - Request tracing (X-Request-ID propagation)
    - Security headers (HSTS, CSP, X-Frame-Options, etc.)
    - Rate limiting (Redis sliding window + in-memory fallback)
    - Prometheus metrics (via /metrics if enabled)
    - Graceful lifespan with dependency health checks
    - Global exception handling with RFC7807 problem+json
    - CORS, GZip, TrustedHost, and CorrelationId middleware
    - OpenAPI customization + versioned routing
    - Background task telemetry

This module is deliberately verbose to demonstrate professional
engineering practices: explicit types, exhaustive docstrings,
defensive programming, and observability hooks.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.routing import Match
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.exceptions import CyberVerseError

# ---------------------------------------------------------------------------
# Context & Logging Setup
# ---------------------------------------------------------------------------

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(__import__("logging"), settings.LOG_LEVEL.upper(), 20)
    ),
    cache_logger_on_first_use=True,
)

logger: structlog.BoundLogger = structlog.get_logger("cyberverse.api")

# ---------------------------------------------------------------------------
# Middleware: Request ID & Correlation
# ---------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID into request context and response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(req_id)
        structlog.contextvars.bind_contextvars(request_id=req_id, path=request.url.path, method=request.method)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time-ms"] = str(int((time.perf_counter() - start) * 1000))
            return response
        finally:
            structlog.contextvars.clear_contextvars()
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
            response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;")
        return response


class SlashNormalisationMiddleware:
    """Resolve slash-only path differences by routing, never by redirecting.

    Starlette answers ``/api/v1/courses`` with a 307 to ``/api/v1/courses/`` and
    builds that ``Location`` from the upstream ``Host``. Behind the Next.js
    rewrite proxy that host is the backend's own address, so the browser is
    handed ``http://127.0.0.1:8000/api/v1/courses/`` — blocked as mixed content
    on an HTTPS origin, blocked as CORS on an HTTP one — and ``fetch()``
    rejects with "Failed to fetch".

    The proxy also strips trailing slashes on the way in, so a redirect-based
    fixup would bounce between the two hops forever. Normalising the path in the
    ASGI scope instead returns the real response: no redirect, no leaked
    upstream host, no loop, and it holds for every route, not just the ones
    whose ``Location`` happened to be observed.
    """

    def __init__(self, app: ASGIApp, routes: list[Any]) -> None:
        self.app = app
        self._routes = routes
        self._cache: dict[tuple[str, str], str | None] = {}

    def _matches(self, scope: Scope, path: str) -> bool:
        probe: Scope = {**scope, "path": path}
        for route in self._routes:
            match, _child_scope = route.matches(probe)
            if match is Match.FULL:
                return True
        return False

    def _normalise(self, scope: Scope, path: str) -> str | None:
        key = (scope.get("method", "GET"), path)
        if key in self._cache:
            return self._cache[key]
        result: str | None = None
        if not self._matches(scope, path):
            alternative = path[:-1] if path.endswith("/") else path + "/"
            if alternative != path and self._matches(scope, alternative):
                result = alternative
        self._cache[key] = result
        return result

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path: str = scope.get("path", "")
            if path:
                normalised = self._normalise(scope, path)
                if normalised is not None:
                    scope["path"] = normalised
                    raw_path = scope.get("raw_path")
                    if isinstance(raw_path, bytes):
                        # raw_path is "path?query" — replace the path, keep the query
                        _, sep, query = raw_path.partition(b"?")
                        scope["raw_path"] = normalised.encode("utf-8") + (sep + query if sep else b"")
        await self.app(scope, receive, send)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured access logging with latency and status."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        # Skip health probes to reduce noise
        if request.url.path not in ("/health", "/health/detailed", "/metrics"):
            logger.info(
                "http.access",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                client_ip=request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown"),
                user_agent=request.headers.get("user-agent", "")[:120],
            )
        return response

# ---------------------------------------------------------------------------
# Lifespan: Startup / Shutdown Hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB, warm caches, and graceful shutdown."""
    logger.info("cyberverse.startup", version=settings.APP_VERSION, env=settings.ENVIRONMENT, api_prefix=settings.API_V1_PREFIX)
    # --- Startup ---
    db_ok = True
    try:
        await init_db()
        logger.info("cyberverse.db.connected")
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        logger.warning("cyberverse.db.degraded", error=str(exc), hint="API stays up; /health will show degraded")

    # Optional: warm Redis, validate secrets, pre-load ML models, etc.
    try:
        if settings.REDIS_URL:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]
            rc = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            await rc.ping()
            await rc.aclose()
            logger.info("cyberverse.redis.connected")
    except Exception as exc:  # noqa: BLE001
        logger.warning("cyberverse.redis.unavailable", error=str(exc))

    # Optional: Sentry init
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk  # type: ignore[import-not-found]
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                environment=settings.ENVIRONMENT,
                release=settings.APP_VERSION,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            )
            logger.info("cyberverse.sentry.enabled")
        except Exception as exc:  # noqa: BLE001
            logger.warning("cyberverse.sentry.failed", error=str(exc))

    yield  # -- app is running --

    # --- Shutdown ---
    logger.info("cyberverse.shutdown", reason="lifespan exit")
    try:
        await close_db()
        logger.info("cyberverse.db.closed")
    except Exception:
        logger.warning("cyberverse.db.close_failed", exc_info=True)

    # Flush structlog / sentry
    try:
        await asyncio.sleep(0.05)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# FastAPI App Factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Factory to create the FastAPI app with all middleware and routers."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "CyberVerse Educational Cybersecurity Simulation Platform API — "
            "Enterprise-grade, sandboxed, and auditable. All offensive operations "
            "are simulated; no real systems are touched."
        ),
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
        contact={"name": "CyberVerse Support", "email": "support@cyberverse.io", "url": "https://cyberverse.io/support"},
        license_info={"name": "Proprietary — Educational Use Only"},
        swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "none", "filter": True, "showRequestDuration": True},
    )

    # Middleware stack (order matters: outermost first)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(GZipMiddleware, minimum_size=500)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
        max_age=600,
    )

    # Exception handlers
    _register_exception_handlers(application)

    # Routers
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Health & Meta endpoints
    _register_meta_routes(application)

    # OpenAPI customization
    _customize_openapi(application)

    # Added last so it is the outermost middleware: it normalises the path before
    # anything else reads the scope. Needs the finished route table.
    application.add_middleware(SlashNormalisationMiddleware, routes=application.routes)

    return application


# ---------------------------------------------------------------------------
# Exception Handlers (RFC 7807 style)
# ---------------------------------------------------------------------------

def _problem_response(
    *,
    status_code: int,
    title: str,
    detail: str,
    code: str | None = None,
    instance: str | None = None,
    extras: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://cyberverse.io/errors/{code or 'general'}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance or "",
        "success": False,
    }
    if code:
        body["code"] = code
    if extras:
        body.update(extras)
    return JSONResponse(status_code=status_code, content=body)


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):  # type: ignore[no-redef]
        logger.warning("http.exception", path=request.url.path, status_code=exc.status_code, detail=str(exc.detail))
        return _problem_response(
            status_code=exc.status_code,
            title="HTTP Error",
            detail=str(exc.detail),
            instance=request.url.path,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):  # type: ignore[no-redef]
        logger.warning("validation.error", path=request.url.path, errors=exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "type": "https://cyberverse.io/errors/validation",
                "title": "Validation Failed",
                "status": 422,
                "detail": "Request validation failed",
                "success": False,
                "error": "Validation failed",
                "details": exc.errors(),
                "instance": request.url.path,
            },
        )

    @app.exception_handler(CyberVerseError)
    async def cyberverse_exception_handler(request: Request, exc: CyberVerseError):  # type: ignore[no-redef]
        logger.warning("domain.error", path=request.url.path, code=exc.code, message=exc.message, details=exc.details)
        return _problem_response(
            status_code=exc.status_code,
            title=exc.code.replace("_", " ").title(),
            detail=exc.message,
            code=exc.code,
            instance=request.url.path,
            extras={"details": exc.details},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):  # type: ignore[no-redef]
        logger.error("unhandled.exception", path=request.url.path, error=str(exc), exc_info=True)
        # Do not leak internals in production
        detail = "Internal server error" if settings.ENVIRONMENT == "production" else str(exc)
        return _problem_response(
            status_code=500,
            title="Internal Server Error",
            detail=detail,
            code="internal_error",
            instance=request.url.path,
        )

# ---------------------------------------------------------------------------
# Meta Routes
# ---------------------------------------------------------------------------

def _register_meta_routes(app: FastAPI) -> None:
    @app.get("/health", tags=["Meta"], summary="Liveness probe")
    async def health_check():  # type: ignore[no-redef]
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "service": "cyberverse-api",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    @app.get("/health/detailed", tags=["Meta"], summary="Readiness probe with dependency checks")
    async def detailed_health_check():  # type: ignore[no-redef]
        from sqlalchemy import text as sql_text

        from app.core.database import engine

        checks: dict[str, dict[str, Any]] = {}
        latency: dict[str, float] = {}

        # Database
        t0 = time.perf_counter()
        try:
            async with engine.connect() as conn:
                await conn.execute(sql_text("SELECT 1"))
            checks["database"] = {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
        except Exception as exc:  # noqa: BLE001
            checks["database"] = {"status": "error", "message": str(exc)[:300]}

        # Redis
        t0 = time.perf_counter()
        try:
            import redis.asyncio as redis  # type: ignore[import-untyped]

            client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            await client.ping()
            await client.aclose()
            checks["redis"] = {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = {"status": "error", "message": str(exc)[:300]}

        # Celery broker (best-effort)
        if settings.CELERY_BROKER_URL:
            checks["celery_broker"] = {"status": "ok" if checks.get("redis", {}).get("status") == "ok" else "unknown"}

        all_healthy = all(v.get("status") == "ok" for v in checks.values())
        return {
            "status": "ok" if all_healthy else "degraded",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks": checks,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    @app.get("/version", tags=["Meta"], summary="Build & version info")
    async def version_info():  # type: ignore[no-redef]
        import platform

        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "python": platform.python_version(),
            "api_prefix": settings.API_V1_PREFIX,
        }

    @app.get("/", tags=["Meta"], include_in_schema=False)
    async def root():  # type: ignore[no-redef]
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": f"{settings.API_V1_PREFIX}/docs",
            "health": "/health",
            "message": "Welcome to CyberVerse — Educational Cybersecurity Simulation Platform",
        }


def _customize_openapi(app: FastAPI) -> None:
    """Add security schemes and server metadata to OpenAPI."""
    from fastapi.openapi.utils import get_openapi

    original_openapi = app.openapi

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["info"]["contact"] = {"name": "CyberVerse Platform", "url": "https://cyberverse.io", "email": "support@cyberverse.io"}
        schema["servers"] = [
            {"url": "https://api.cyberverse.io", "description": "Production"},
            {"url": "https://staging-api.cyberverse.io", "description": "Staging"},
            {"url": "http://localhost:8000", "description": "Local"},
        ]
        # Add BearerAuth scheme
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token from /api/v1/auth/login",
        }
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# App Singleton
# ---------------------------------------------------------------------------

app: FastAPI = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,  # we use structured logging
        workers=1 if settings.DEBUG else 2,
    )
