"""
Schemas for breach simulation requests and responses.

The simulation system is entirely deterministic — no randomness,
no ML. Every run with the same inputs produces the same output.
"""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    canvas_id: uuid.UUID
    scenario: str = Field(
        description="Pre-defined scenario ID or 'custom'",
        pattern=r"^(compromised_device|stolen_credential|insider_threat|"
                r"expired_certificate|lateral_from_dmz|data_exfiltration|"
                r"privilege_escalation|supply_chain|custom)$",
    )
    # For custom scenarios
    source_node_id: str | None = None
    target_node_id: str | None = None
    attacker_properties: dict[str, Any] = Field(default_factory=dict)


class AttackStep(BaseModel):
    """One step in the simulated attack path."""
    step_number: int
    from_node: str
    to_node: str
    edge_id: str | None = None
    action: str  # "traverse", "blocked", "exploit"
    result: Literal["allowed", "blocked", "partial"]
    reason: str
    risk_contribution: float  # how much this step adds to total risk score


class SimulationResult(BaseModel):
    """Complete simulation output."""
    simulation_id: str
    scenario: str
    risk_score: float = Field(ge=0, le=100)
    risk_level: Literal["critical", "high", "medium", "low", "minimal"]
    attack_path: list[AttackStep]
    blocked_at: AttackStep | None = None
    total_steps: int
    successful_steps: int

    # Visual overlay data for the frontend
    highlighted_nodes: list[str]  # node IDs to highlight
    highlighted_edges: list[str]  # edge IDs to highlight
    compromised_nodes: list[str]  # nodes the attacker reached

    recommendations: list[str]
    summary: str


# ── Pre-defined scenario configs ─────────────────────────────
# These define the starting conditions for each built-in scenario

SCENARIO_CONFIGS: dict[str, dict[str, Any]] = {
    "compromised_device": {
        "name": "Compromised Endpoint Device",
        "description": "An endpoint device is compromised via malware. Simulates lateral movement attempts.",
        "attacker_starts_at": "device",
        "attacker_properties": {
            "has_valid_credential": False,
            "device_compliant": False,
            "mfa_completed": False,
        },
    },
    "stolen_credential": {
        "name": "Stolen User Credential",
        "description": "Valid credentials obtained via phishing. Tests access controls beyond password auth.",
        "attacker_starts_at": "identity",
        "attacker_properties": {
            "has_valid_credential": True,
            "device_compliant": True,
            "mfa_completed": False,
        },
    },
    "insider_threat": {
        "name": "Insider Threat",
        "description": "Authenticated user with legitimate access attempts unauthorized data access.",
        "attacker_starts_at": "identity",
        "attacker_properties": {
            "has_valid_credential": True,
            "device_compliant": True,
            "mfa_completed": True,
            "is_insider": True,
        },
    },
    "expired_certificate": {
        "name": "Expired Certificate / Stale Session",
        "description": "Service-to-service communication with expired TLS cert or stale session token.",
        "attacker_starts_at": "application",
        "attacker_properties": {
            "has_valid_credential": False,
            "certificate_valid": False,
            "session_expired": True,
        },
    },
    "lateral_from_dmz": {
        "name": "Lateral Movement from DMZ",
        "description": "Attacker gains foothold in DMZ and attempts to reach internal resources.",
        "attacker_starts_at": "network_segment",
        "attacker_properties": {
            "has_valid_credential": False,
            "device_compliant": False,
            "in_dmz": True,
        },
    },
    "data_exfiltration": {
        "name": "Data Exfiltration Attempt",
        "description": "Compromised account tries to access and exfiltrate classified data.",
        "attacker_starts_at": "identity",
        "attacker_properties": {
            "has_valid_credential": True,
            "mfa_completed": True,
            "device_compliant": True,
            "attempting_exfiltration": True,
        },
    },
    "privilege_escalation": {
        "name": "Privilege Escalation via Service Account",
        "description": "Compromised service account attempts to escalate to admin-level access.",
        "attacker_starts_at": "application",
        "attacker_properties": {
            "has_valid_credential": True,
            "is_service_account": True,
            "attempting_escalation": True,
        },
    },
    "supply_chain": {
        "name": "Supply Chain Compromise",
        "description": "Third-party application dependency is compromised. Tests trust boundaries.",
        "attacker_starts_at": "application",
        "attacker_properties": {
            "has_valid_credential": True,
            "is_third_party": True,
            "device_compliant": False,
        },
    },
}
