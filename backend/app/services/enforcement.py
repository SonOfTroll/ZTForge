"""
Enforcement service — demonstrates policy enforcement via OPA.

This is an MVP-level demonstration, not a production proxy.
It shows how canvas-defined policies translate to runtime access decisions
by querying OPA with the request context.
"""

from typing import Any

from app.services.policy_engine import PolicyEngine
from app.core.logging import get_logger, audit_log

logger = get_logger("ztforge.enforcement")


class EnforcementService:
    def __init__(self, policy_engine: PolicyEngine | None = None):
        self.engine = policy_engine or PolicyEngine()

    async def check_access(
        self,
        source: str,
        target: str,
        user_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate whether a request from source to target should be allowed.
        Queries OPA with the full request context.
        """
        opa_input = {
            "source": source,
            "target": target,
            "user": user_context,
            "timestamp": user_context.get("timestamp", ""),
        }

        result = await self.engine.evaluate("ztforge/canvas", opa_input)
        allowed = result.get("allow", False)

        await audit_log(
            action="enforcement_decision",
            user_id=user_context.get("user_id", "system"),
            resource_type="access_check",
            resource_id=f"{source}->{target}",
            details={"allowed": allowed, "reason": result.get("reason", "")},
        )

        return {
            "allowed": allowed,
            "source": source,
            "target": target,
            "reason": result.get("reason", "Policy decision"),
            "evaluated_by": "opa",
        }

    async def sync_canvas_to_opa(
        self,
        canvas_id: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        policies: list[dict[str, Any]],
    ) -> bool:
        """
        Push canvas state to OPA as data so policies can reference it.
        Called when canvas is saved or policies change.
        """
        canvas_data = {
            "nodes": {n["id"]: n for n in nodes},
            "edges": {e["id"]: e for e in edges},
            "policies": {p.get("id", str(i)): p for i, p in enumerate(policies)},
        }

        success = await self.engine.push_data(
            f"ztforge/canvases/{canvas_id}", canvas_data
        )
        if success:
            logger.info("canvas_synced_to_opa", canvas_id=canvas_id)
        return success
