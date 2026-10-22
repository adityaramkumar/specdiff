from __future__ import annotations

import re
from pathlib import Path

from specdiff.agents.context import NodeContext
from specdiff.build.files import strip_header
from specdiff.graph import SpecGraph, ancestors
from specdiff.types import HashMap, SpecdiffConfig

_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]*$|[._](test|spec)\.[^/]+$")


def is_test_path(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def output_relative(path: str, output_dir: str) -> str | None:
    try:
        return Path(path).relative_to(output_dir).as_posix()
    except ValueError:
        return None


def _read(paths: list[str], output_dir: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in paths:
        rel = output_relative(path, output_dir)
        if rel is not None and Path(path).exists():
            files[rel] = strip_header(Path(path).read_text("utf-8"))
    return files


def node_context(
    node_id: str, graph: SpecGraph, hm: HashMap, config: SpecdiffConfig
) -> NodeContext:
    """Gather the specs and on-disk code an agent needs to build node_id."""
    node = graph.nodes[node_id]
    out = config.output_dir
    dep_paths = [p for d in node.depends_on if d in hm.nodes for p in hm.nodes[d].generated_files]
    own = hm.nodes[node_id].generated_files if node_id in hm.nodes else []
    others = {
        rel: owner
        for owner, entry in hm.nodes.items()
        if owner != node_id
        for p in entry.generated_files
        if (rel := output_relative(p, out)) is not None
    }
    return NodeContext(
        node=node,
        language=node.language or config.language,
        output_dir=out,
        ancestors=ancestors(graph, node_id),
        deps=[graph.nodes[d] for d in node.depends_on],
        # Dependency tests are noise for the agent; their code is the contract.
        dep_files=_read([p for p in dep_paths if not is_test_path(p)], out),
        own_files=_read(own, out),
        others=others,
        acceptance={p: Path(p).read_text("utf-8") for p in node.acceptance if Path(p).is_file()},
        test_framework=config.test_framework,
        test_command=config.test_command,
        check_command=config.check_command,
    )
