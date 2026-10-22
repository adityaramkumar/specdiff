from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field

from specdiff.types import SpecNode


@dataclass
class SpecGraph:
    nodes: dict[str, SpecNode] = field(default_factory=dict)
    # Reverse edges: prerequisite id -> ids that depend on it or are its children.
    dependents: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def prerequisites(node: SpecNode) -> list[str]:
    """Nodes whose content feeds into this one: its dependencies and its parent."""
    return [*node.depends_on, *([node.parent] if node.parent else [])]


def build_graph(nodes: list[SpecNode]) -> SpecGraph:
    """Build a graph from spec nodes.

    Raises ValueError for duplicate IDs, missing depends_on or parent targets,
    a child that is unlocked under a locked parent, or a cycle.
    """
    graph = SpecGraph()
    for node in nodes:
        if node.id in graph.nodes:
            raise ValueError(
                f"Duplicate spec ID '{node.id}': {node.file_path} and "
                f"{graph.nodes[node.id].file_path}"
            )
        graph.nodes[node.id] = node

    for node in nodes:
        for dep_id in node.depends_on:
            if dep_id not in graph.nodes:
                raise ValueError(f"{node.id} depends on {dep_id}, but that spec does not exist.")
        if node.parent is not None:
            if node.parent not in graph.nodes:
                raise ValueError(
                    f"{node.id} declares parent '{node.parent}', but that spec does not exist."
                )
            parent = graph.nodes[node.parent]
            if parent.status == "locked" and node.status != "locked":
                raise ValueError(
                    f"{node.id} has status '{node.status}' but parent "
                    f"'{parent.id}' is locked — unlock the parent first."
                )
        for prereq in prerequisites(node):
            graph.dependents[prereq].append(node.id)

    topo_sort(graph, graph.nodes)
    return graph


def topo_sort(graph: SpecGraph, node_ids: Iterable[str]) -> list[str]:
    """Return node_ids with prerequisites first. Ties keep ID order for stable output.

    Raises ValueError on a cycle.
    """
    id_set = set(node_ids)
    in_degree = {
        nid: sum(1 for p in prerequisites(graph.nodes[nid]) if p in id_set) for nid in id_set
    }
    queue = deque(sorted(nid for nid, deg in in_degree.items() if deg == 0))
    result: list[str] = []

    while queue:
        nid = queue.popleft()
        result.append(nid)
        for dependent in sorted(graph.dependents.get(nid, [])):
            if dependent in in_degree:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    if len(result) != len(id_set):
        remaining = id_set - set(result)
        raise ValueError(f"Circular dependency detected among: {', '.join(sorted(remaining))}")
    return result


def upstream(graph: SpecGraph, start_ids: Iterable[str]) -> set[str]:
    """All transitive prerequisites of start_ids, excluding start_ids themselves."""
    start = set(start_ids)
    seen: set[str] = set()
    queue = deque(start)
    while queue:
        for prereq in prerequisites(graph.nodes[queue.popleft()]):
            if prereq not in seen:
                seen.add(prereq)
                queue.append(prereq)
    return seen - start


def ancestors(graph: SpecGraph, node_id: str) -> list[SpecNode]:
    """The parent chain of node_id, root first."""
    chain: list[SpecNode] = []
    parent = graph.nodes[node_id].parent
    while parent is not None:
        chain.append(graph.nodes[parent])
        parent = graph.nodes[parent].parent
    return list(reversed(chain))


def impact_summary(graph: SpecGraph, changed_ids: list[str]) -> dict:
    """Return the downstream nodes of changed_ids with their cascade depth."""
    depths: dict[str, int] = {}
    queue = deque((nid, 0) for nid in changed_ids)
    visited: set[str] = set(changed_ids)
    while queue:
        nid, depth = queue.popleft()
        for dep in graph.dependents.get(nid, []):
            if dep not in visited:
                visited.add(dep)
                depths[dep] = depth + 1
                queue.append((dep, depth + 1))

    return {
        "changed": changed_ids,
        "downstream": dict(sorted(depths.items())),
        "cascade_depth": max(depths.values(), default=0),
        "total": len(changed_ids) + len(depths),
    }
