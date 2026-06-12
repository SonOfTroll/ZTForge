"""
Input validators beyond what Pydantic handles.

These catch domain-specific invalid states that schema validation
alone can't express (e.g., graph cycles, orphaned edges).
"""

import re
from typing import Any


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Remove potentially dangerous content from user-provided strings.
    Not a replacement for parameterized queries — this is defense in depth.
    """
    # Strip null bytes
    value = value.replace("\x00", "")
    # Truncate
    value = value[:max_length]
    return value.strip()


def validate_canvas_nodes(nodes: list[dict[str, Any]]) -> list[str]:
    """
    Validate canvas node structure. Returns list of error messages.
    Empty list = valid.
    """
    errors: list[str] = []
    seen_ids: set[str] = set()
    valid_types = {
        "identity", "device", "application", "data",
        "network_segment", "policy_gate",
    }

    for i, node in enumerate(nodes):
        node_id = node.get("id")
        if not node_id or not isinstance(node_id, str):
            errors.append(f"Node at index {i}: missing or invalid id")
            continue

        if node_id in seen_ids:
            errors.append(f"Duplicate node id: {node_id}")
        seen_ids.add(node_id)

        data = node.get("data", {})
        node_type = data.get("node_type")
        if node_type not in valid_types:
            errors.append(
                f"Node {node_id}: invalid type '{node_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )

        pos = node.get("position", {})
        if not isinstance(pos.get("x"), (int, float)):
            errors.append(f"Node {node_id}: missing or invalid position.x")
        if not isinstance(pos.get("y"), (int, float)):
            errors.append(f"Node {node_id}: missing or invalid position.y")

    return errors


def validate_canvas_edges(
    edges: list[dict[str, Any]], node_ids: set[str]
) -> list[str]:
    """Validate edges reference existing nodes."""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, edge in enumerate(edges):
        edge_id = edge.get("id")
        if not edge_id:
            errors.append(f"Edge at index {i}: missing id")
            continue

        if edge_id in seen_ids:
            errors.append(f"Duplicate edge id: {edge_id}")
        seen_ids.add(edge_id)

        source = edge.get("source")
        target = edge.get("target")

        if source not in node_ids:
            errors.append(f"Edge {edge_id}: source '{source}' not found in nodes")
        if target not in node_ids:
            errors.append(f"Edge {edge_id}: target '{target}' not found in nodes")
        if source == target:
            errors.append(f"Edge {edge_id}: self-loop detected (source == target)")

    return errors


def validate_rego_syntax(content: str) -> list[str]:
    """
    Basic Rego syntax validation. Not a full parser — just catches
    obvious errors before sending to OPA.
    """
    errors: list[str] = []

    if not content.strip():
        errors.append("Rego content is empty")
        return errors

    # Must have a package declaration
    if not re.search(r"^package\s+\w+", content, re.MULTILINE):
        errors.append("Missing 'package' declaration")

    # Check for balanced braces
    open_braces = content.count("{")
    close_braces = content.count("}")
    if open_braces != close_braces:
        errors.append(
            f"Unbalanced braces: {open_braces} opening, {close_braces} closing"
        )

    return errors
