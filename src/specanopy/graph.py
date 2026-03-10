from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from specanopy.types import SpecNode


@dataclass
class SpecGraph:
    nodes: dict[str, SpecNode] = field(default_factory=dict)
    dependents: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def build_graph(nodes: list[SpecNode]) -> SpecGraph:
    """Build a dependency graph from spec nodes.

    Raises ValueError if any depends_on target or parent reference does not exist,
    or if a child contradicts a parent's frontmatter fields.
    """
    graph = SpecGraph()
    graph.nodes = {n.id: n for n in nodes}

    for node in nodes:
        for dep_id in node.depends_on:
            if dep_id not in graph.nodes:
                raise ValueError(f"{node.id} depends on {dep_id}, but that spec does not exist.")
            graph.dependents[dep_id].append(node.id)

    _validate_parents(graph)

    return graph


def _validate_parents(graph: SpecGraph) -> None:
    """Check that parent references exist and children don't contradict parent fields."""
    for node in graph.nodes.values():
        if node.parent is None:
            continue
        if node.parent not in graph.nodes:
            raise ValueError(
                f"{node.id} declares parent '{node.parent}', but that spec does not exist."
            )
        parent = graph.nodes[node.parent]
        if parent.status != node.status:
            raise ValueError(
                f"{node.id} has status '{node.status}' which conflicts with "
                f"parent '{parent.id}' status '{parent.status}'."
            )


def topo_sort(graph: SpecGraph, node_ids: list[str]) -> list[str]:
    """Return node_ids in topological order (dependencies before dependents).

    Raises ValueError on circular dependencies.
    """
    id_set = set(node_ids)

    in_degree: dict[str, int] = {nid: 0 for nid in id_set}
    for nid in id_set:
        for dep_id in graph.nodes[nid].depends_on:
            if dep_id in id_set:
                in_degree[nid] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        nid = queue.popleft()
        result.append(nid)
        for dependent in graph.dependents.get(nid, []):
            if dependent in in_degree:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    if len(result) != len(id_set):
        remaining = id_set - set(result)
        raise ValueError(f"Circular dependency detected among: {', '.join(sorted(remaining))}")

    return result


def _collect_downstream(graph: SpecGraph, start_ids: set[str]) -> set[str]:
    """Walk dependents transitively to collect all downstream nodes."""
    visited: set[str] = set()
    queue = deque(start_ids)
    while queue:
        nid = queue.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        for dep in graph.dependents.get(nid, []):
            if dep not in visited:
                queue.append(dep)
    return visited


def _collect_stale_upstream(
    graph: SpecGraph,
    start_ids: set[str],
    stale_ids: set[str],
) -> set[str]:
    """Walk upstream transitively to include stale dependencies."""
    visited: set[str] = set()
    queue = deque(start_ids)

    while queue:
        nid = queue.popleft()
        for dep_id in graph.nodes[nid].depends_on:
            if dep_id not in stale_ids or dep_id in visited:
                continue
            visited.add(dep_id)
            queue.append(dep_id)

    return visited


def cascade(
    graph: SpecGraph,
    changed_ids: list[str],
    stale_ids: set[str] | None = None,
) -> list[str]:
    """Compute the full rebuild set for a list of changed nodes.

    Walks downstream (dependents) from changed nodes, and also walks upstream
    to include any stale dependencies. Returns everything in topological order.
    """
    all_ids = set(changed_ids)

    if stale_ids is not None:
        all_ids |= _collect_stale_upstream(graph, all_ids, stale_ids)

    downstream = _collect_downstream(graph, all_ids)
    all_ids |= downstream

    return topo_sort(graph, list(all_ids))


def impact_summary(graph: SpecGraph, changed_ids: list[str]) -> dict:
    """Return a structured summary of the cascade impact."""
    downstream = _collect_downstream(graph, set(changed_ids)) - set(changed_ids)

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

    max_depth = max(depths.values()) if depths else 0

    return {
        "changed": changed_ids,
        "downstream": {nid: depths.get(nid, 0) for nid in sorted(downstream)},
        "cascade_depth": max_depth,
        "total": len(changed_ids) + len(downstream),
    }
