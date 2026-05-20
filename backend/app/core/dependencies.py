"""
FastAPI dependencies for DI.

Keeps route handlers clean — auth, DB sessions, and role checks
are injected rather than repeated in every endpoint.
"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.security import RateLimiter, TokenPayload, decode_access_token

# ── Database Engine ──────────────────────────────────────────
# Lazy-initialized on first request. Connection pooling is handled
# by SQLAlchemy's default QueuePool.
_engine = None
_session_factory = None


def _get_engine(settings: Settings):
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            str(settings.database_url),
            echo=settings.debug,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,  # detect stale connections
        )
    return _engine


def _get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = _get_engine(settings)
        _session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncSession:  # type: ignore[misc]
    """Yield a DB session per request, rolled back on error."""
    factory = _get_session_factory(settings)
    async with factory() as session:
        try:
            yield session  # type: ignore[misc]
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis ────────────────────────────────────────────────────
_redis_pool: aioredis.Redis | None = None


async def get_redis(
    settings: Annotated[Settings, Depends(get_settings)],
) -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            str(settings.redis_url),
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


# ── Auth ─────────────────────────────────────────────────────
async def get_current_user(request: Request) -> TokenPayload:
    """
    Extract and validate JWT from Authorization header.
    Called as a dependency on every protected route.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = await decode_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# ── Rate Limit Dependency ────────────────────────────────────
async def check_rate_limit(
    user: Annotated[TokenPayload, Depends(get_current_user)],
    redis_client: Annotated[aioredis.Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPayload:
    """
    Enforces per-user rate limiting. Returns the user payload if allowed,
    raises 429 if limit exceeded.
    """
    limiter = RateLimiter(
        redis_client,
        max_requests=settings.rate_limit_per_second,
        window_seconds=1,
    )
    allowed = await limiter.check(user.sub)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )
    return user


# ── Role Guards ──────────────────────────────────────────────
# These return dependency functions that check minimum role level.

def require_role(*allowed_roles: str):
    """
    Factory for role-checking dependencies.
    Usage: Depends(require_role("admin", "editor"))
    """
    async def _guard(
        user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        if not any(role in user.realm_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(allowed_roles)}",
            )
        return user

    return _guard


# Convenience aliases for common role checks
RequireAdmin = Depends(require_role("admin"))
RequireEditor = Depends(require_role("admin", "editor"))
RequireViewer = Depends(require_role("admin", "editor", "viewer"))
