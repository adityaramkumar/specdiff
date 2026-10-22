from __future__ import annotations

from pathlib import Path

import click

from specdiff import hashmap
from specdiff.config import load_config
from specdiff.graph import SpecGraph, build_graph
from specdiff.plan import NodeState, compute_states, skills_hash
from specdiff.types import HashMap, SpecdiffConfig, SpecNode

SPEC_EVAL_SKILL = "spec-eval"


def project_config() -> tuple[SpecdiffConfig, Path]:
    config = load_config(Path(".specdiff"))
    return config, Path(config.specs_dir)


def load_graph(nodes: list[SpecNode]) -> SpecGraph:
    try:
        return build_graph(nodes)
    except ValueError as exc:
        raise click.ClickException(f"{exc}\nRun `specdiff validate` to see every problem.") from exc


def load_states(
    config: SpecdiffConfig, specs_dir: Path, nodes: list[SpecNode]
) -> tuple[SpecGraph, HashMap, dict[str, NodeState]]:
    graph = load_graph(nodes)
    hm = hashmap.load(specs_dir)
    return graph, hm, compute_states(graph, hm, config, skills_hash(specs_dir))
