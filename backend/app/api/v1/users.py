"""
User management endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import check_rate_limit, get_db
from app.core.security import TokenPayload
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_my_profile(
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(User).where(User.keycloak_id == user.sub)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if not db_user:
        return {
            "sub": user.sub,
            "email": user.email,
            "display_name": user.preferred_username,
            "role": user.highest_role,
            "synced": False,
        }
    return {
        "id": str(db_user.id),
        "email": db_user.email,
        "display_name": db_user.display_name,
        "role": db_user.role,
        "organization": db_user.organization,
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
        "synced": True,
    }
