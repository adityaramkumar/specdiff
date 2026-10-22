from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from specdiff.graph import SpecGraph, prerequisites, topo_sort, upstream
from specdiff.skills import load_build_skills
from specdiff.types import HashMap, SpecdiffConfig


@dataclass
class NodeState:
    """Whether a node's last build is still valid, and if not, why."""

    inputs: dict[str, str]
    fingerprint: str
    reasons: list[str] = field(default_factory=list)
    is_new: bool = False
    context: bool = False

    @property
    def stale(self) -> bool:
        return not self.context and (self.is_new or bool(self.reasons))

    @property
    def label(self) -> str:
        if self.context:
            return "context"
        return "new" if self.is_new else "stale" if self.reasons else "current"


def skills_hash(specs_dir: Path) -> str:
    """Hash of the effective build skills, built-in defaults included."""
    return _digest(load_build_skills(specs_dir))


def compute_states(
    graph: SpecGraph, hm: HashMap, config: SpecdiffConfig, skills_digest: str
) -> dict[str, NodeState]:
    """Fingerprint every node and diff it against the last recorded build.

    A node's fingerprint covers everything that shapes its generated code: its own
    spec, the fingerprints of its dependencies and parent (so changes propagate
    downstream), the build skills, and the model/language/test settings.
    """
    states: dict[str, NodeState] = {}
    for nid in topo_sort(graph, graph.nodes):
        node = graph.nodes[nid]
        inputs = {
            "spec": node.hash,
            "skills": skills_digest,
            "model": config.model,
            "language": node.language or config.language,
            "test_framework": config.test_framework or "",
        }
        for dep_id in node.depends_on:
            inputs[f"dep:{dep_id}"] = states[dep_id].fingerprint
        if node.parent:
            inputs[f"parent:{node.parent}"] = states[node.parent].fingerprint
        for path in node.acceptance:
            inputs[f"acceptance:{path}"] = file_digest(Path(path))

        state = NodeState(inputs=inputs, fingerprint=_digest(inputs))
        entry = hm.nodes.get(nid)
        if not node.generate:
            state.context = True
        elif entry is None:
            state.is_new = True
        elif entry.inputs:
            state.reasons = _diff_reasons(entry.inputs, inputs)
        else:
            # Hash maps written before fingerprints only recorded the spec hash.
            if entry.spec_hash != node.hash:
                state.reasons.append("spec changed")
            state.reasons += [f"{p} changed" for p in prerequisites(node) if states[p].stale]
        states[nid] = state
    return states


_EDGE_NAMES = {"dep": "dependency", "parent": "parent", "acceptance": "acceptance test"}


def _diff_reasons(old: dict[str, str], new: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    for key in sorted(old.keys() | new.keys(), key=lambda k: (":" in k, k)):
        before, after = old.get(key), new.get(key)
        if before == after:
            continue
        kind, _, name = key.partition(":")
        if name and before is None:
            reasons.append(f"{_EDGE_NAMES[kind]} {name} added")
        elif name and after is None:
            reasons.append(f"{_EDGE_NAMES[kind]} {name} removed")
        elif name:
            reasons.append(f"{name} changed")
        elif kind in ("spec", "skills"):
            reasons.append(f"{kind} changed")
        else:
            reasons.append(f"{kind} changed ({before or 'none'} -> {after or 'none'})")
    return reasons


@dataclass
class BuildPlan:
    order: list[str]
    blocked: dict[str, str]


def plan_build(
    graph: SpecGraph, states: dict[str, NodeState], target: str | None = None
) -> BuildPlan:
    """Pick the stale nodes to build, prerequisites first.

    With a target, only the target and its prerequisites are considered. Draft
    specs are never built, and neither is anything downstream of one.
    """
    scope = set(graph.nodes) if target is None else {target} | upstream(graph, [target])
    blocked: dict[str, str] = {}
    order: list[str] = []
    for nid in topo_sort(graph, scope):
        if not states[nid].stale:
            continue
        node = graph.nodes[nid]
        if node.status == "draft":
            blocked[nid] = "draft"
        elif waiting_on := next((p for p in prerequisites(node) if p in blocked), None):
            blocked[nid] = f"waits on {waiting_on}"
        else:
            order.append(nid)
    return BuildPlan(order=order, blocked=blocked)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def _digest(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
