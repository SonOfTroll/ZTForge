"""
Tests for breach simulation engine.

These test the core deterministic rules — no mocks needed since
the simulator is a pure function of its inputs.
"""

import pytest
from app.services.simulator import BreachSimulator
from app.schemas.simulation import SimulationRequest


def _make_nodes():
    """Minimal canvas with identity → app → data path."""
    return [
        {"id": "user-1", "type": "identity", "position": {"x": 0, "y": 0}, "data": {"label": "Engineer", "node_type": "identity", "properties": {"segment": "corp"}}},
        {"id": "app-1", "type": "application", "position": {"x": 200, "y": 0}, "data": {"label": "API Server", "node_type": "application", "properties": {"segment": "corp"}}},
        {"id": "data-1", "type": "data", "position": {"x": 400, "y": 0}, "data": {"label": "Customer DB", "node_type": "data", "properties": {"segment": "restricted"}}},
        {"id": "device-1", "type": "device", "position": {"x": 0, "y": 200}, "data": {"label": "Laptop", "node_type": "device", "properties": {"segment": "corp"}}},
    ]


def _make_edges_with_policies():
    """Edges with realistic Zero Trust policies."""
    return [
        {
            "id": "edge-1", "source": "user-1", "target": "app-1",
            "policy": {"action": "allow", "conditions": {"require_mfa": True, "require_valid_credential": True}},
        },
        {
            "id": "edge-2", "source": "app-1", "target": "data-1",
            "policy": {"action": "allow", "conditions": {"require_compliant_device": True, "enforce_microsegmentation": True, "require_valid_credential": True}},
        },
        {
            "id": "edge-3", "source": "device-1", "target": "app-1",
            "policy": {"action": "deny"},
        },
    ]


def _make_edges_no_policies():
    """Edges with no explicit policies — should all be denied."""
    return [
        {"id": "edge-1", "source": "user-1", "target": "app-1"},
        {"id": "edge-2", "source": "app-1", "target": "data-1"},
    ]


class TestDefaultDeny:
    """NIST 800-207 Tenet: Default deny — no explicit allow means blocked."""

    def test_no_policy_blocks_traversal(self):
        sim = BreachSimulator(_make_nodes(), _make_edges_no_policies(), [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="stolen_credential",
            source_node_id="user-1",
        )
        result = sim.run(req)
        assert result.successful_steps == 0
        assert result.risk_score == 0.0
        assert all(s.result == "blocked" for s in result.attack_path)

    def test_deny_policy_blocks(self):
        sim = BreachSimulator(_make_nodes(), _make_edges_with_policies(), [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="compromised_device",
            source_node_id="device-1",
        )
        result = sim.run(req)
        # device-1 → app-1 has deny policy
        blocked_step = next((s for s in result.attack_path if s.from_node == "device-1"), None)
        assert blocked_step is not None
        assert blocked_step.result == "blocked"


class TestMFAEnforcement:
    """MFA requirement blocks attackers without completed MFA."""

    def test_stolen_cred_without_mfa_blocked(self):
        sim = BreachSimulator(_make_nodes(), _make_edges_with_policies(), [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="stolen_credential",
            source_node_id="user-1",
        )
        result = sim.run(req)
        # Stolen cred has has_valid_credential=True but mfa_completed=False
        mfa_block = next((s for s in result.attack_path if "MFA" in s.reason), None)
        assert mfa_block is not None
        assert mfa_block.result == "blocked"

    def test_insider_with_mfa_passes_first_edge(self):
        sim = BreachSimulator(_make_nodes(), _make_edges_with_policies(), [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="insider_threat",
            source_node_id="user-1",
        )
        result = sim.run(req)
        # Insider has valid cred + MFA, should pass user→app edge
        first_step = result.attack_path[0] if result.attack_path else None
        assert first_step is not None
        assert first_step.result == "allowed"


class TestMicrosegmentation:
    """Cross-segment traffic should be blocked when microsegmentation is enforced."""

    def test_cross_segment_blocked(self):
        sim = BreachSimulator(_make_nodes(), _make_edges_with_policies(), [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="insider_threat",
            source_node_id="user-1",
        )
        result = sim.run(req)
        # app-1 (corp) → data-1 (restricted) with microsegmentation enforced
        cross_seg = next(
            (s for s in result.attack_path if s.from_node == "app-1" and s.to_node == "data-1"),
            None,
        )
        assert cross_seg is not None
        assert cross_seg.result == "blocked"
        assert "segmentation" in cross_seg.reason.lower()


class TestRiskScoring:
    """Risk score should reflect the severity of the breach."""

    def test_fully_blocked_is_zero_risk(self):
        sim = BreachSimulator(_make_nodes(), _make_edges_no_policies(), [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="compromised_device",
            source_node_id="device-1",
        )
        result = sim.run(req)
        assert result.risk_score == 0.0
        assert result.risk_level == "minimal"

    def test_risk_increases_with_access(self):
        # Use edges that allow everything
        permissive_edges = [
            {"id": "e1", "source": "user-1", "target": "app-1", "policy": {"action": "allow", "conditions": {}}},
            {"id": "e2", "source": "app-1", "target": "data-1", "policy": {"action": "allow", "conditions": {}}},
        ]
        sim = BreachSimulator(_make_nodes(), permissive_edges, [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="insider_threat",
            source_node_id="user-1",
        )
        result = sim.run(req)
        assert result.risk_score > 0
        assert result.successful_steps > 0
        assert len(result.compromised_nodes) > 1


class TestRecommendations:
    def test_recommends_mfa_when_missing(self):
        permissive_edges = [
            {"id": "e1", "source": "user-1", "target": "app-1", "policy": {"action": "allow", "conditions": {}}},
        ]
        sim = BreachSimulator(_make_nodes(), permissive_edges, [])
        req = SimulationRequest(
            canvas_id="00000000-0000-0000-0000-000000000001",
            scenario="compromised_device",
            source_node_id="user-1",
            attacker_properties={"has_valid_credential": True},
        )
        result = sim.run(req)
        assert any("MFA" in r or "mfa" in r.lower() for r in result.recommendations)
