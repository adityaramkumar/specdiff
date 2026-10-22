from __future__ import annotations

from specdiff.graph import build_graph
from specdiff.plan import compute_states, plan_build
from specdiff.types import HashMap, HashMapEntry, SpecdiffConfig, SpecNode


def _node(id: str, depends_on=None, parent=None, status="approved", h=None) -> SpecNode:
    return SpecNode(
        id=id,
        version="1.0.0",
        status=status,
        hash=h or f"hash-{id}",
        content=f"content for {id}",
        file_path=f".specdiff/{id}.spec.md",
        parent=parent,
        depends_on=depends_on or [],
    )


def _built(nodes, config=None, skills="s1") -> HashMap:
    """A hash map recording that every node was built in its current state."""
    graph = build_graph(nodes)
    states = compute_states(graph, HashMap(), config or SpecdiffConfig(), skills)
    return HashMap(
        nodes={
            nid: HashMapEntry(
                spec_hash=graph.nodes[nid].hash,
                generated_files=[],
                generated_at="",
                inputs=st.inputs,
            )
            for nid, st in states.items()
        }
    )


def _states(nodes, hm, config=None, skills="s1"):
    graph = build_graph(nodes)
    return graph, compute_states(graph, hm, config or SpecdiffConfig(), skills)


class TestComputeStates:
    def test_new_nodes(self):
        _, states = _states([_node("a")], HashMap())
        assert states["a"].label == "new"

    def test_unchanged_is_current(self):
        nodes = [_node("a"), _node("b", depends_on=["a"])]
        _, states = _states(nodes, _built(nodes))
        assert not states["a"].stale and not states["b"].stale

    def test_dependency_change_propagates_transitively(self):
        nodes = [_node("a"), _node("b", depends_on=["a"]), _node("c", depends_on=["b"])]
        hm = _built(nodes)
        changed = [_node("a", h="new"), nodes[1], nodes[2]]
        _, states = _states(changed, hm)

        assert states["a"].reasons == ["spec changed"]
        assert states["b"].reasons == ["a changed"]
        assert states["c"].reasons == ["b changed"]

    def test_parent_change_marks_children_stale(self):
        nodes = [_node("root"), _node("child", parent="root")]
        hm = _built(nodes)
        _, states = _states([_node("root", h="new"), nodes[1]], hm)
        assert states["child"].reasons == ["root changed"]

    def test_skills_and_model_changes(self):
        nodes = [_node("a")]
        hm = _built(nodes)
        _, states = _states(nodes, hm, SpecdiffConfig(model="grok-4"), skills="s2")
        assert states["a"].reasons == [
            "model changed (gemini-2.5-flash -> grok-4)",
            "skills changed",
        ]

    def test_added_dependency(self):
        hm = _built([_node("a"), _node("b")])
        _, states = _states([_node("a"), _node("b", depends_on=["a"])], hm)
        assert states["b"].reasons == ["dependency a added"]

    def test_legacy_entry_uses_spec_hash_and_prereqs(self):
        hm = HashMap(
            nodes={
                "a": HashMapEntry(spec_hash="old", generated_files=[], generated_at=""),
                "b": HashMapEntry(spec_hash="hash-b", generated_files=[], generated_at=""),
                "c": HashMapEntry(spec_hash="hash-c", generated_files=[], generated_at=""),
            }
        )
        _, states = _states([_node("a"), _node("b", depends_on=["a"]), _node("c")], hm)
        assert states["a"].reasons == ["spec changed"]
        assert states["b"].reasons == ["a changed"]
        assert not states["c"].stale


class TestPlanBuild:
    def test_orders_prerequisites_first(self):
        nodes = [_node("c", depends_on=["b"]), _node("b", parent="a"), _node("a")]
        graph, states = _states(nodes, HashMap())
        assert plan_build(graph, states).order == ["a", "b", "c"]

    def test_skips_current_nodes(self):
        nodes = [_node("a"), _node("b", depends_on=["a"])]
        hm = _built(nodes)
        graph, states = _states([nodes[0], _node("b", depends_on=["a"], h="new")], hm)
        assert plan_build(graph, states).order == ["b"]

    def test_target_includes_stale_prereqs_not_downstream(self):
        nodes = [_node("a"), _node("b", depends_on=["a"]), _node("c", depends_on=["b"])]
        graph, states = _states(nodes, HashMap())
        assert plan_build(graph, states, "b").order == ["a", "b"]

    def test_stale_draft_blocks_itself_and_dependents(self):
        nodes = [_node("a", status="draft"), _node("b", depends_on=["a"]), _node("c")]
        graph, states = _states(nodes, HashMap())
        plan = plan_build(graph, states)
        assert plan.order == ["c"]
        assert plan.blocked == {"a": "draft", "b": "waits on a"}

    def test_current_draft_does_not_block(self):
        built = [_node("a"), _node("b", depends_on=["a"])]
        hm = _built(built)
        nodes = [_node("a", status="draft"), _node("b", depends_on=["a"], h="new")]
        graph, states = _states(nodes, hm)
        plan = plan_build(graph, states)
        assert plan.order == ["b"] and plan.blocked == {}
