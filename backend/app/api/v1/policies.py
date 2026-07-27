"""
Policy CRUD endpoints.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import check_rate_limit, get_db
from app.core.logging import audit_log
from app.core.security import TokenPayload
from app.models.canvas import Canvas
from app.models.policy import Policy
from app.models.user import User
from app.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreate,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Verify canvas exists and user has access
    canvas = await db.get(Canvas, body.canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    db_user = (await db.execute(select(User).where(User.keycloak_id == user.sub))).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    is_owner = canvas.owner_id == db_user.id
    if not is_owner and not user.is_editor:
        raise HTTPException(status_code=403, detail="Edit permission required")

    policy = Policy(
        name=body.name,
        policy_type=body.policy_type,
        description=body.description,
        rego_content=body.rego_content,
        rules=body.rules,
        attached_to=body.attached_to,
        canvas_id=body.canvas_id,
    )
    db.add(policy)
    await db.flush()
    await audit_log("policy_created", user.sub, "policy", str(policy.id))
    return policy


@router.get("/canvas/{canvas_id}", response_model=list[PolicyResponse])
async def list_policies_for_canvas(
    canvas_id: uuid.UUID,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(Policy).where(Policy.canvas_id == canvas_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdate,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    await audit_log("policy_updated", user.sub, "policy", str(policy_id))
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(policy)
    await audit_log("policy_deleted", user.sub, "policy", str(policy_id))
