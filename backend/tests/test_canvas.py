"""
Tests for canvas schema validation and OCC.
"""

import pytest
from pydantic import ValidationError
from app.schemas.canvas import CanvasCreate, CanvasUpdate, CanvasNode, CanvasEdge, EdgePolicy, NodeData, Position


class TestCanvasCreate:
    def test_valid_create(self):
        c = CanvasCreate(title="My ZT Architecture")
        assert c.title == "My ZT Architecture"
        assert c.visibility == "private"

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            CanvasCreate(title="")

    def test_long_title_rejected(self):
        with pytest.raises(ValidationError):
            CanvasCreate(title="x" * 201)


class TestCanvasUpdate:
    def test_version_required(self):
        with pytest.raises(ValidationError):
            CanvasUpdate()  # missing version

    def test_partial_update(self):
        u = CanvasUpdate(title="New Title", version=3)
        assert u.title == "New Title"
        assert u.nodes is None  # not provided = unchanged


class TestCanvasNode:
    def test_valid_node(self):
        node = CanvasNode(
            id="node-1",
            type="identity",
            position=Position(x=100, y=200),
            data=NodeData(label="Admin User", node_type="identity"),
        )
        assert node.id == "node-1"

    def test_node_with_properties(self):
        node = CanvasNode(
            id="dev-1",
            type="device",
            position=Position(x=0, y=0),
            data=NodeData(
                label="Workstation",
                node_type="device",
                compliance_status="compliant",
                properties={"os": "linux", "agent_version": "2.1"},
            ),
        )
        assert node.data.compliance_status == "compliant"


class TestEdgePolicy:
    def test_default_deny(self):
        p = EdgePolicy()
        assert p.action == "deny"

    def test_allow_with_conditions(self):
        p = EdgePolicy(
            action="allow",
            conditions={"require_mfa": True, "require_compliant_device": True},
        )
        assert p.conditions["require_mfa"] is True
