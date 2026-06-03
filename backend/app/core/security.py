"""
JWT validation against Keycloak JWKS endpoint + rate limiting.

Design notes:
- JWKS keys are cached with TTL to avoid hammering Keycloak on every request.
- Rate limiting uses a sliding window counter in Redis, keyed by user sub.
- We extract Keycloak roles from the `realm_access.roles` claim, not from
  a custom claim, because that's where Keycloak puts them by default.
"""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.backends import RSAKey

from app.core.config import Settings, get_settings


@dataclass
class JWKSCache:
    """Holds JWKS keys with a TTL so we re-fetch periodically."""

    keys: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: float = 0.0
    ttl_seconds: float = 300.0  # 5 minutes

    @property
    def is_stale(self) -> bool:
        return time.monotonic() - self.fetched_at > self.ttl_seconds


# Module-level singleton — intentional, avoids DI overhead for a cache
_jwks_cache = JWKSCache()


async def fetch_jwks(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Fetch JWKS from Keycloak, with caching."""
    global _jwks_cache
    if not _jwks_cache.is_stale and _jwks_cache.keys:
        return _jwks_cache.keys

    s = settings or get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(s.keycloak_jwks_url)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])

    _jwks_cache = JWKSCache(keys=keys, fetched_at=time.monotonic())
    return keys


def _find_rsa_key(
    keys: list[dict[str, Any]], kid: str
) -> dict[str, Any] | None:
    for key in keys:
        if key.get("kid") == kid and key.get("kty") == "RSA":
            return key
    return None


@dataclass
class TokenPayload:
    """Validated token claims we actually use."""

    sub: str
    email: str
    preferred_username: str
    realm_roles: list[str]
    exp: int

    @property
    def is_admin(self) -> bool:
        return "admin" in self.realm_roles

    @property
    def is_editor(self) -> bool:
        return "editor" in self.realm_roles or self.is_admin

    @property
    def highest_role(self) -> str:
        for role in ("admin", "editor", "viewer"):
            if role in self.realm_roles:
                return role
        return "guest"


async def decode_access_token(
    token: str, settings: Settings | None = None
) -> TokenPayload:
    """
    Validate and decode a Keycloak-issued JWT.

    Raises ValueError on any validation failure — caller should map this
    to a 401 response.
    """
    s = settings or get_settings()

    try:
        # Peek at header to find kid without full validation
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise ValueError(f"Malformed token header: {e}") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("Token missing kid header")

    keys = await fetch_jwks(s)
    rsa_key = _find_rsa_key(keys, kid)

    if rsa_key is None:
        # Key rotation may have happened — force refresh once
        _jwks_cache.fetched_at = 0.0
        keys = await fetch_jwks(s)
        rsa_key = _find_rsa_key(keys, kid)
        if rsa_key is None:
            raise ValueError(f"No matching RSA key for kid={kid}")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=s.keycloak_client_id,
            issuer=s.keycloak_issuer_url,
            options={"verify_at_hash": False},
        )
    except JWTError as e:
        raise ValueError(f"Token validation failed: {e}") from e

    # Extract realm roles from Keycloak's default claim structure
    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    return TokenPayload(
        sub=payload["sub"],
        email=payload.get("email", ""),
        preferred_username=payload.get("preferred_username", ""),
        realm_roles=roles,
        exp=payload["exp"],
    )


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis.

    Each user gets a sorted set keyed by their sub claim. Entries are
    timestamps; we trim entries older than the window and check count.
    """

    def __init__(self, redis_client: Any, max_requests: int = 10, window_seconds: int = 1):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, user_id: str) -> bool:
        """Returns True if request is allowed, False if rate-limited."""
        key = f"ratelimit:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        pipe = self.redis.pipeline()
        # Remove entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count remaining entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set TTL so keys don't leak if user goes idle
        pipe.expire(key, self.window_seconds * 2)

        results = await pipe.execute()
        current_count = results[1]

        return current_count < self.max_requests
