from __future__ import annotations

import pytest

from specanopy.graph import build_graph, cascade, impact_summary, topo_sort
from specanopy.types import SpecNode


def _make_node(
    id: str,
    depends_on: list[str] | None = None,
    parent: str | None = None,
    status: str = "approved",
) -> SpecNode:
    return SpecNode(
        id=id,
        version="1.0.0",
        status=status,
        hash=f"hash-{id}",
        content=f"content for {id}",
        file_path=f".specanopy/{id}.spec.md",
        parent=parent,
        depends_on=depends_on or [],
    )


class TestBuildGraph:
    def test_simple_chain(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        assert "b" in graph.dependents["a"]
        assert "c" in graph.dependents["b"]
        assert graph.dependents.get("c", []) == []

    def test_orphaned_reference(self):
        a = _make_node("a", depends_on=["nonexistent"])
        with pytest.raises(ValueError, match="a depends on nonexistent"):
            build_graph([a])

    def test_no_dependencies(self):
        a = _make_node("a")
        b = _make_node("b")
        graph = build_graph([a, b])

        assert graph.dependents.get("a", []) == []
        assert graph.dependents.get("b", []) == []


class TestParentValidation:
    def test_valid_parent(self):
        parent = _make_node("auth")
        child = _make_node("auth/login", parent="auth")
        graph = build_graph([parent, child])
        assert "auth/login" in graph.nodes

    def test_orphaned_parent(self):
        child = _make_node("auth/login", parent="nonexistent")
        with pytest.raises(ValueError, match="declares parent 'nonexistent'"):
            build_graph([child])

    def test_status_conflict(self):
        parent = _make_node("auth", status="locked")
        child = _make_node("auth/login", parent="auth", status="draft")
        with pytest.raises(ValueError, match="conflicts with parent"):
            build_graph([parent, child])

    def test_matching_status_ok(self):
        parent = _make_node("auth", status="approved")
        child = _make_node("auth/login", parent="auth", status="approved")
        graph = build_graph([parent, child])
        assert "auth/login" in graph.nodes


class TestTopoSort:
    def test_linear_chain(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        result = topo_sort(graph, ["a", "b", "c"])
        assert result.index("a") < result.index("b") < result.index("c")

    def test_diamond(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["a"])
        d = _make_node("d", depends_on=["b", "c"])
        graph = build_graph([a, b, c, d])

        result = topo_sort(graph, ["a", "b", "c", "d"])
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")

    def test_cycle_detected(self):
        a = _make_node("a", depends_on=["c"])
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        with pytest.raises(ValueError, match="Circular dependency"):
            topo_sort(graph, ["a", "b", "c"])

    def test_subset_of_nodes(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        result = topo_sort(graph, ["a", "b"])
        assert result == ["a", "b"]


class TestCascade:
    def test_single_change_cascades_down(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        result = cascade(graph, ["a"])
        assert set(result) == {"a", "b", "c"}
        assert result.index("a") < result.index("b") < result.index("c")

    def test_leaf_change_no_downstream(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        graph = build_graph([a, b])

        result = cascade(graph, ["b"])
        assert result == ["b"]

    def test_multiple_roots(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c")
        d = _make_node("d", depends_on=["c"])
        graph = build_graph([a, b, c, d])

        result = cascade(graph, ["a", "c"])
        assert set(result) == {"a", "b", "c", "d"}

    def test_includes_stale_upstream_deps(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        graph = build_graph([a, b])

        result = cascade(graph, ["b"], stale_ids={"a", "b"})
        assert set(result) == {"a", "b"}
        assert result.index("a") < result.index("b")

    def test_includes_transitive_stale_upstream_deps(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        result = cascade(graph, ["c"], stale_ids={"a", "b", "c"})
        assert set(result) == {"a", "b", "c"}
        assert result.index("a") < result.index("b") < result.index("c")


class TestImpactSummary:
    def test_structure(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        summary = impact_summary(graph, ["a"])
        assert summary["changed"] == ["a"]
        assert "b" in summary["downstream"]
        assert "c" in summary["downstream"]
        assert summary["downstream"]["b"] == 1
        assert summary["downstream"]["c"] == 2
        assert summary["cascade_depth"] == 2
        assert summary["total"] == 3

    def test_no_downstream(self):
        a = _make_node("a")
        graph = build_graph([a])

        summary = impact_summary(graph, ["a"])
        assert summary["downstream"] == {}
        assert summary["cascade_depth"] == 0
        assert summary["total"] == 1
