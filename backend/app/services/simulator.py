"""
Breach simulation engine — deterministic, rule-based, zero ML.

Implements NIST 800-207 Zero Trust principles as graph traversal rules.
The simulator treats the canvas as a directed graph and attempts to find
paths from the attacker's position to target resources.
"""

import uuid
from typing import Any

from app.schemas.simulation import (
    AttackStep,
    SCENARIO_CONFIGS,
    SimulationRequest,
    SimulationResult,
)


class BreachSimulator:
    def __init__(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        policies: list[dict[str, Any]],
    ):
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = edges
        self.policies_by_element: dict[str, dict[str, Any]] = {}
        for p in policies:
            attached = p.get("attached_to")
            if attached:
                self.policies_by_element[attached] = p
        self.adjacency: dict[str, list[dict[str, Any]]] = {}
        for edge in edges:
            src = edge["source"]
            if src not in self.adjacency:
                self.adjacency[src] = []
            self.adjacency[src].append(edge)

    def run(self, request: SimulationRequest) -> SimulationResult:
        scenario_config = SCENARIO_CONFIGS.get(request.scenario, {})
        attacker_props = {
            **scenario_config.get("attacker_properties", {}),
            **request.attacker_properties,
        }
        source_id = request.source_node_id
        if not source_id:
            source_id = self._find_starting_node(
                scenario_config.get("attacker_starts_at", "identity")
            )
        if not source_id or source_id not in self.nodes:
            return self._empty_result(request.scenario, "No valid source node found")

        attack_path: list[AttackStep] = []
        visited: set[str] = set()
        compromised: set[str] = {source_id}
        frontier: list[str] = [source_id]
        blocked_at: AttackStep | None = None
        step_num = 0

        while frontier:
            current = frontier.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for edge in self.adjacency.get(current, []):
                target_id = edge["target"]
                if target_id in visited:
                    continue
                step_num += 1
                step = self._evaluate_edge(step_num, current, target_id, edge, attacker_props)
                attack_path.append(step)
                if step.result == "allowed":
                    compromised.add(target_id)
                    frontier.append(target_id)
                elif step.result == "blocked" and blocked_at is None:
                    blocked_at = step

        risk_score = self._calculate_risk_score(compromised, attack_path, attacker_props)
        risk_level = self._risk_level(risk_score)
        successful = sum(1 for s in attack_path if s.result == "allowed")
        recommendations = self._generate_recommendations(attack_path, compromised, attacker_props)
        highlighted_edges = [s.edge_id for s in attack_path if s.edge_id and s.result == "allowed"]

        return SimulationResult(
            simulation_id=str(uuid.uuid4()),
            scenario=request.scenario,
            risk_score=risk_score,
            risk_level=risk_level,
            attack_path=attack_path,
            blocked_at=blocked_at,
            total_steps=len(attack_path),
            successful_steps=successful,
            highlighted_nodes=list(visited),
            highlighted_edges=highlighted_edges,
            compromised_nodes=list(compromised),
            recommendations=recommendations,
            summary=self._build_summary(request.scenario, risk_score, successful, len(attack_path), blocked_at),
        )

    def _evaluate_edge(self, step_num: int, from_id: str, to_id: str, edge: dict[str, Any], attacker_props: dict[str, Any]) -> AttackStep:
        edge_id = edge.get("id")
        policy = edge.get("policy") or self.policies_by_element.get(edge_id, {})
        if "rules" in policy:
            action = policy["rules"].get("action", "deny")
            conditions = policy["rules"].get("conditions", {})
        else:
            action = policy.get("action", "deny")
            conditions = policy.get("conditions", {})

        # Rule 1: No explicit allow = blocked
        if action != "allow":
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason="No explicit allow policy (default deny)", risk_contribution=0.0)

        # Rule 2: Device compliance
        if conditions.get("require_compliant_device") and not attacker_props.get("device_compliant"):
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason="Device compliance check failed", risk_contribution=0.0)

        # Rule 3: MFA
        if conditions.get("require_mfa") and not attacker_props.get("mfa_completed"):
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason="MFA required but not completed", risk_contribution=0.0)

        # Rule 4: Credential validity
        if conditions.get("require_valid_credential", True) and not attacker_props.get("has_valid_credential"):
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason="Valid credential required", risk_contribution=0.0)

        # Rule 5: Time-based restriction
        if conditions.get("allowed_hours") and attacker_props.get("outside_business_hours"):
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason=f"Time restriction: {conditions['allowed_hours']}", risk_contribution=0.0)

        # Rule 6: Micro-segmentation
        from_seg = self.nodes.get(from_id, {}).get("data", {}).get("properties", {}).get("segment")
        to_seg = self.nodes.get(to_id, {}).get("data", {}).get("properties", {}).get("segment")
        if conditions.get("enforce_microsegmentation") and from_seg and to_seg and from_seg != to_seg and not conditions.get("allow_cross_segment"):
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason=f"Micro-segmentation violation: {from_seg} → {to_seg}", risk_contribution=0.0)

        # Rule 7: Certificate validity
        if conditions.get("require_valid_certificate") and attacker_props.get("certificate_valid") is False:
            return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="blocked", reason="Certificate expired or revoked", risk_contribution=0.0)

        # All checks passed
        target_type = self.nodes.get(to_id, {}).get("data", {}).get("node_type", "unknown")
        risk = self._risk_for_node_type(target_type, attacker_props)
        return AttackStep(step_number=step_num, from_node=from_id, to_node=to_id, edge_id=edge_id, action="traverse", result="allowed", reason=f"All checks passed — reached {target_type}", risk_contribution=risk)

    def _risk_for_node_type(self, node_type: str, attacker_props: dict[str, Any]) -> float:
        base = {"data": 25.0, "application": 15.0, "identity": 10.0, "device": 8.0, "network_segment": 5.0, "policy_gate": 3.0}
        risk = base.get(node_type, 5.0)
        if attacker_props.get("is_insider"):
            risk *= 1.3
        if attacker_props.get("is_service_account"):
            risk *= 1.2
        return min(risk, 30.0)

    def _calculate_risk_score(self, compromised: set[str], path: list[AttackStep], attacker_props: dict[str, Any]) -> float:
        if not path or not self.nodes:
            return 0.0
        risk_sum = sum(s.risk_contribution for s in path if s.result == "allowed")
        coverage = len(compromised) / len(self.nodes) * 20.0
        return round(min(risk_sum + coverage, 100.0), 1)

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 80: return "critical"
        if score >= 60: return "high"
        if score >= 40: return "medium"
        if score >= 20: return "low"
        return "minimal"

    def _find_starting_node(self, node_type: str) -> str | None:
        for nid, node in self.nodes.items():
            if node.get("data", {}).get("node_type") == node_type:
                return nid
        return next(iter(self.nodes), None)

    def _generate_recommendations(self, path: list[AttackStep], compromised: set[str], attacker_props: dict[str, Any]) -> list[str]:
        recs: list[str] = []
        allowed_count = sum(1 for s in path if s.result == "allowed")
        if not attacker_props.get("mfa_completed") and allowed_count > 0:
            recs.append("Enable MFA on all access paths")
        if allowed_count > 3:
            recs.append("Review access policies — attacker traversed multiple edges")
        for nid in compromised:
            node = self.nodes.get(nid, {})
            if node.get("data", {}).get("node_type") == "data":
                recs.append(f"Data node '{node.get('data', {}).get('label', nid)}' is reachable — add controls")
        if not attacker_props.get("device_compliant") and allowed_count > 0:
            recs.append("Enable device compliance checks")
        if len(compromised) > len(self.nodes) * 0.5:
            recs.append("Implement micro-segmentation — >50% nodes reachable")
        if not recs:
            recs.append("Zero Trust policies effectively contained the breach")
        return recs

    def _build_summary(self, scenario: str, risk_score: float, successful: int, total: int, blocked_at: AttackStep | None) -> str:
        name = SCENARIO_CONFIGS.get(scenario, {}).get("name", scenario)
        parts = [f"Scenario: {name}.", f"Risk: {risk_score}/100.", f"Traversed {successful}/{total} edges."]
        if blocked_at:
            parts.append(f"Blocked at step {blocked_at.step_number}: {blocked_at.reason}")
        elif successful == total and total > 0:
            parts.append("WARNING: Attacker was not blocked.")
        return " ".join(parts)

    def _empty_result(self, scenario: str, reason: str) -> SimulationResult:
        return SimulationResult(simulation_id=str(uuid.uuid4()), scenario=scenario, risk_score=0.0, risk_level="minimal", attack_path=[], blocked_at=None, total_steps=0, successful_steps=0, highlighted_nodes=[], highlighted_edges=[], compromised_nodes=[], recommendations=[reason], summary=reason)
