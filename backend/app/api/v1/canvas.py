"""
Canvas CRUD endpoints with optimistic concurrency control.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import check_rate_limit, get_db, require_role
from app.core.logging import audit_log
from app.core.security import TokenPayload
from app.models.canvas import Canvas
from app.models.user import User
from app.schemas.canvas import (
    CanvasCreate,
    CanvasListItem,
    CanvasResponse,
    CanvasUpdate,
)
from app.utils.validators import validate_canvas_edges, validate_canvas_nodes

router = APIRouter(prefix="/canvases", tags=["canvas"])


@router.post("", response_model=CanvasResponse, status_code=status.HTTP_201_CREATED)
async def create_canvas(
    body: CanvasCreate,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Resolve internal user ID from keycloak sub
    stmt = select(User).where(User.keycloak_id == user.sub)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found — login first")

    canvas = Canvas(
        title=body.title,
        description=body.description,
        visibility=body.visibility,
        owner_id=db_user.id,
        nodes=[],
        edges=[],
    )
    db.add(canvas)
    await db.flush()
    await audit_log("canvas_created", user.sub, "canvas", str(canvas.id))
    return canvas


@router.get("", response_model=list[CanvasListItem])
async def list_canvases(
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(User).where(User.keycloak_id == user.sub)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if not db_user:
        return []

    # Users see their own canvases + public ones
    stmt = (
        select(Canvas)
        .where(
            (Canvas.owner_id == db_user.id) | (Canvas.visibility == "public")
        )
        .order_by(Canvas.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{canvas_id}", response_model=CanvasResponse)
async def get_canvas(
    canvas_id: uuid.UUID,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    canvas = await _get_canvas_or_404(db, canvas_id, user)
    return canvas


@router.patch("/{canvas_id}", response_model=CanvasResponse)
async def update_canvas(
    canvas_id: uuid.UUID,
    body: CanvasUpdate,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    canvas = await _get_canvas_or_404(db, canvas_id, user, require_edit=True)

    # Optimistic concurrency control
    if body.version != canvas.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Version conflict",
                "server_version": canvas.version,
                "client_version": body.version,
                "message": "Canvas was modified by another user. Reload and retry.",
            },
        )

    # Validate nodes/edges if provided
    if body.nodes is not None:
        node_dicts = [n.model_dump() for n in body.nodes]
        errors = validate_canvas_nodes(node_dicts)
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})
        canvas.nodes = node_dicts

    if body.edges is not None:
        edge_dicts = [e.model_dump() for e in body.edges]
        node_ids = {n["id"] for n in (canvas.nodes or [])}
        errors = validate_canvas_edges(edge_dicts, node_ids)
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})
        canvas.edges = edge_dicts

    if body.title is not None:
        canvas.title = body.title
    if body.description is not None:
        canvas.description = body.description
    if body.viewport is not None:
        canvas.viewport = body.viewport

    canvas.version += 1
    await audit_log("canvas_updated", user.sub, "canvas", str(canvas_id))
    return canvas


@router.delete("/{canvas_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_canvas(
    canvas_id: uuid.UUID,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    canvas = await _get_canvas_or_404(db, canvas_id, user, require_edit=True)
    await db.delete(canvas)
    await audit_log("canvas_deleted", user.sub, "canvas", str(canvas_id))


async def _get_canvas_or_404(
    db: AsyncSession,
    canvas_id: uuid.UUID,
    user: TokenPayload,
    require_edit: bool = False,
) -> Canvas:
    stmt = select(Canvas).where(Canvas.id == canvas_id)
    result = await db.execute(stmt)
    canvas = result.scalar_one_or_none()
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    # Resolve user
    stmt = select(User).where(User.keycloak_id == user.sub)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    # Access control
    is_owner = db_user and canvas.owner_id == db_user.id
    if canvas.visibility == "private" and not is_owner and not user.is_admin:
        raise HTTPException(status_code=404, detail="Canvas not found")
    if require_edit and not is_owner and not user.is_editor:
        raise HTTPException(status_code=403, detail="Edit permission required")

    return canvas
