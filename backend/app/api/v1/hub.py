"""
Policy Hub — community template marketplace with fork support.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import check_rate_limit, get_db
from app.core.logging import audit_log
from app.core.security import TokenPayload
from app.models.template import Template
from app.models.user import User
from app.schemas.policy import TemplateCreate, TemplateFork, TemplateResponse
from app.services.policy_engine import export_rego, export_pomerium_yaml, export_terraform, export_iptables

router = APIRouter(prefix="/hub", tags=["hub"])


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tag: str | None = None,
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Template).where(Template.visibility == "public")
    if tag:
        stmt = stmt.where(Template.tags.contains([tag]))
    stmt = stmt.order_by(Template.fork_count.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    db_user = (await db.execute(select(User).where(User.keycloak_id == user.sub))).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    template = Template(
        name=body.name,
        description=body.description,
        tags=body.tags,
        canvas_data=body.canvas_data,
        policies_data=body.policies_data,
        visibility=body.visibility,
        author_id=db_user.id,
    )
    db.add(template)
    await db.flush()
    await audit_log("template_created", user.sub, "template", str(template.id))
    return template


@router.post("/templates/{template_id}/fork", response_model=TemplateResponse, status_code=201)
async def fork_template(
    template_id: uuid.UUID,
    body: TemplateFork,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    original = await db.get(Template, template_id)
    if not original:
        raise HTTPException(status_code=404, detail="Template not found")

    db_user = (await db.execute(select(User).where(User.keycloak_id == user.sub))).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    fork = Template(
        name=body.name or f"{original.name} (fork)",
        description=original.description,
        tags=list(original.tags),
        canvas_data=dict(original.canvas_data),
        policies_data=list(original.policies_data),
        forked_from=original.id,
        author_id=db_user.id,
    )
    db.add(fork)
    original.fork_count += 1
    await db.flush()
    await audit_log("template_forked", user.sub, "template", str(fork.id), {"forked_from": str(template_id)})
    return fork


@router.get("/export/{canvas_id}")
async def export_canvas_config(
    canvas_id: uuid.UUID,
    format: str = Query(pattern=r"^(rego|pomerium|terraform|iptables)$"),
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Export canvas as production-ready config in the specified format."""
    from app.models.canvas import Canvas
    canvas = await db.get(Canvas, canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    nodes = canvas.nodes or []
    edges = canvas.edges or []

    exporters = {
        "rego": lambda: export_rego(nodes, edges, []),
        "pomerium": lambda: export_pomerium_yaml(nodes, edges),
        "terraform": lambda: export_terraform(nodes, edges),
        "iptables": lambda: export_iptables(nodes, edges),
    }

    content = exporters[format]()
    content_types = {
        "rego": "text/plain",
        "pomerium": "text/yaml",
        "terraform": "text/plain",
        "iptables": "text/x-shellscript",
    }

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=content, media_type=content_types[format])
