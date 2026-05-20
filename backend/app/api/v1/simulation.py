"""
Simulation endpoint — runs breach scenarios against a canvas.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import check_rate_limit, get_db
from app.core.logging import audit_log
from app.core.security import TokenPayload
from app.models.canvas import Canvas
from app.models.policy import Policy
from app.schemas.simulation import SimulationRequest, SimulationResult, SCENARIO_CONFIGS
from app.services.simulator import BreachSimulator
from sqlalchemy import select

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/run", response_model=SimulationResult)
async def run_simulation(
    body: SimulationRequest,
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    canvas = await db.get(Canvas, body.canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    # Load policies for this canvas
    stmt = select(Policy).where(Policy.canvas_id == body.canvas_id)
    result = await db.execute(stmt)
    policies = result.scalars().all()
    policy_dicts = [
        {
            "id": str(p.id),
            "name": p.name,
            "policy_type": p.policy_type,
            "rules": p.rules,
            "attached_to": p.attached_to,
        }
        for p in policies
    ]

    simulator = BreachSimulator(
        nodes=canvas.nodes or [],
        edges=canvas.edges or [],
        policies=policy_dicts,
    )

    sim_result = simulator.run(body)

    await audit_log(
        "simulation_run",
        user.sub,
        "simulation",
        sim_result.simulation_id,
        details={
            "scenario": body.scenario,
            "risk_score": sim_result.risk_score,
            "canvas_id": str(body.canvas_id),
        },
    )

    return sim_result


@router.get("/scenarios")
async def list_scenarios(
    user: Annotated[TokenPayload, Depends(check_rate_limit)],
):
    """List available breach simulation scenarios."""
    return {
        key: {"name": val["name"], "description": val["description"]}
        for key, val in SCENARIO_CONFIGS.items()
    }
