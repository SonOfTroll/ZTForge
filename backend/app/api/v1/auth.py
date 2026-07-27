"""
Auth routes — Keycloak OIDC integration.

These endpoints handle the OAuth2 authorization code flow with Keycloak.
The frontend redirects to Keycloak for login, Keycloak redirects back
with a code, and we exchange it for tokens.
"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.logging import audit_log
from app.core.security import TokenPayload
from app.models.user import User

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class UserProfile(BaseModel):
    sub: str
    email: str
    display_name: str
    role: str


@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    body: TokenExchangeRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                settings.keycloak_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": body.code,
                    "redirect_uri": body.redirect_uri,
                    "client_id": settings.keycloak_client_id,
                    # Public PKCE client — send verifier instead of secret
                    **(  # type: ignore[arg-type]
                        {"code_verifier": body.code_verifier}
                        if body.code_verifier
                        else {"client_secret": settings.keycloak_client_secret}
                    ),
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token exchange failed: {e.response.text}",
            )

    data = resp.json()

    # Sync user to local DB on first login
    from app.core.security import decode_access_token
    try:
        payload = await decode_access_token(data["access_token"], settings)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token from Keycloak")

    stmt = select(User).where(User.keycloak_id == payload.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            keycloak_id=payload.sub,
            email=payload.email,
            display_name=payload.preferred_username,
            role=payload.highest_role,
        )
        db.add(user)
        await audit_log("user_created", payload.sub, "user")
    else:
        user.role = payload.highest_role
        user.email = payload.email
        await audit_log("user_login", payload.sub, "user")

    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        expires_in=data.get("expires_in", 300),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Refresh an expired access token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                settings.keycloak_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=401, detail="Refresh failed")

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        expires_in=data.get("expires_in", 300),
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(
    user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """Get current user's profile from JWT claims."""
    return UserProfile(
        sub=user.sub,
        email=user.email,
        display_name=user.preferred_username,
        role=user.highest_role,
    )
