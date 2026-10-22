from __future__ import annotations

import pytest

from specdiff.graph import ancestors, build_graph, impact_summary, topo_sort, upstream
from specdiff.types import SpecNode


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
        file_path=f".specdiff/{id}.spec.md",
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

    def test_locked_parent_blocks_non_locked_child(self):
        parent = _make_node("auth", status="locked")
        child = _make_node("auth/login", parent="auth", status="draft")
        with pytest.raises(ValueError, match="is locked"):
            build_graph([parent, child])

    def test_approved_parent_allows_draft_child(self):
        parent = _make_node("auth", status="approved")
        child = _make_node("auth/login", parent="auth", status="draft")
        graph = build_graph([parent, child])
        assert "auth/login" in graph.nodes

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

        with pytest.raises(ValueError, match="Circular dependency"):
            build_graph([a, b, c])

    def test_subset_of_nodes(self):
        a = _make_node("a")
        b = _make_node("b", depends_on=["a"])
        c = _make_node("c", depends_on=["b"])
        graph = build_graph([a, b, c])

        result = topo_sort(graph, ["a", "b"])
        assert result == ["a", "b"]


class TestParentEdges:
    def test_parent_is_a_prerequisite(self):
        root = _make_node("root")
        child = _make_node("child", parent="root")
        graph = build_graph([child, root])

        assert graph.dependents["root"] == ["child"]
        assert topo_sort(graph, ["child", "root"]) == ["root", "child"]

    def test_parent_cycle_detected(self):
        a = _make_node("a", parent="b")
        b = _make_node("b", parent="a")
        with pytest.raises(ValueError, match="Circular"):
            build_graph([a, b])

    def test_duplicate_id_rejected(self):
        with pytest.raises(ValueError, match="Duplicate spec ID 'a'"):
            build_graph([_make_node("a"), _make_node("a")])

    def test_ancestors_root_first(self):
        graph = build_graph(
            [_make_node("root"), _make_node("mid", parent="root"), _make_node("leaf", parent="mid")]
        )
        assert [n.id for n in ancestors(graph, "leaf")] == ["root", "mid"]
        assert ancestors(graph, "root") == []


class TestUpstream:
    def test_transitive_deps_and_parents(self):
        graph = build_graph(
            [
                _make_node("root"),
                _make_node("a"),
                _make_node("b", depends_on=["a"], parent="root"),
                _make_node("c", depends_on=["b"]),
                _make_node("unrelated"),
            ]
        )
        assert upstream(graph, ["c"]) == {"a", "b", "root"}
        assert upstream(graph, ["a"]) == set()


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
