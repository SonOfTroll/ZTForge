"""
Tests for input validators.
"""

from app.utils.validators import (
    sanitize_string,
    validate_canvas_edges,
    validate_canvas_nodes,
    validate_rego_syntax,
)


class TestSanitizeString:
    def test_strips_null_bytes(self):
        assert "\x00" not in sanitize_string("hello\x00world")

    def test_truncates_long_strings(self):
        result = sanitize_string("a" * 5000, max_length=100)
        assert len(result) == 100

    def test_strips_whitespace(self):
        assert sanitize_string("  hello  ") == "hello"


class TestValidateNodes:
    def test_valid_nodes_pass(self):
        nodes = [
            {"id": "n1", "position": {"x": 0, "y": 0}, "data": {"node_type": "identity", "label": "User"}},
            {"id": "n2", "position": {"x": 100, "y": 0}, "data": {"node_type": "device", "label": "Laptop"}},
        ]
        assert validate_canvas_nodes(nodes) == []

    def test_duplicate_ids_detected(self):
        nodes = [
            {"id": "n1", "position": {"x": 0, "y": 0}, "data": {"node_type": "identity", "label": "A"}},
            {"id": "n1", "position": {"x": 100, "y": 0}, "data": {"node_type": "device", "label": "B"}},
        ]
        errors = validate_canvas_nodes(nodes)
        assert any("Duplicate" in e for e in errors)

    def test_invalid_type_rejected(self):
        nodes = [
            {"id": "n1", "position": {"x": 0, "y": 0}, "data": {"node_type": "invalid_type", "label": "X"}},
        ]
        errors = validate_canvas_nodes(nodes)
        assert any("invalid type" in e for e in errors)

    def test_missing_position_detected(self):
        nodes = [
            {"id": "n1", "position": {}, "data": {"node_type": "identity", "label": "X"}},
        ]
        errors = validate_canvas_nodes(nodes)
        assert len(errors) >= 1


class TestValidateEdges:
    def test_valid_edges_pass(self):
        edges = [{"id": "e1", "source": "n1", "target": "n2"}]
        assert validate_canvas_edges(edges, {"n1", "n2"}) == []

    def test_orphaned_source_detected(self):
        edges = [{"id": "e1", "source": "missing", "target": "n2"}]
        errors = validate_canvas_edges(edges, {"n1", "n2"})
        assert any("not found" in e for e in errors)

    def test_self_loop_detected(self):
        edges = [{"id": "e1", "source": "n1", "target": "n1"}]
        errors = validate_canvas_edges(edges, {"n1"})
        assert any("self-loop" in e for e in errors)


class TestRegoValidation:
    def test_valid_rego(self):
        rego = """package ztforge.test\n\ndefault allow := false\n\nallow if {\n    input.user == "admin"\n}"""
        assert validate_rego_syntax(rego) == []

    def test_missing_package(self):
        errors = validate_rego_syntax("default allow := false")
        assert any("package" in e for e in errors)

    def test_unbalanced_braces(self):
        errors = validate_rego_syntax("package test\nallow if {")
        assert any("brace" in e.lower() for e in errors)
