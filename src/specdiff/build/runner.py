from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import click

from specdiff import hashmap
from specdiff.agents.pipeline import PipelineConfig, run_node
from specdiff.agents.stages import Usage
from specdiff.build.checks import run_command
from specdiff.build.files import BACKUP_DIR, NodeWriter, resolve_output_path
from specdiff.build.project import node_context
from specdiff.graph import SpecGraph, prerequisites
from specdiff.skills import load_build_skills
from specdiff.types import HashMap, SpecdiffConfig, SpecNode


class BuildRefused(click.ClickException):
    """The build could not start; nothing was changed."""


@dataclass
class BuildReport:
    built: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)

    @property
    def ok(self) -> bool:
        return not self.failed and not self.skipped


def preflight(ordered_nodes: list[SpecNode], config: SpecdiffConfig, hm: HashMap,
              specs_dir: Path, force: bool) -> None:  # fmt: skip
    """Refuse to build when doing so could lose work or blame the wrong spec."""
    if (specs_dir / BACKUP_DIR).exists():
        raise BuildRefused(
            f"{specs_dir / BACKUP_DIR} exists from an interrupted build. Copy back any files "
            "you need from it, then delete it before building again."
        )
    edited = [
        f for n in ordered_nodes if (e := hm.nodes.get(n.id)) for f in hashmap.modified_files(e)
    ]
    if edited and not force:
        listing = "\n".join(f"  {f}" for f in edited)
        raise BuildRefused(
            f"These generated files were edited by hand since the last build:\n{listing}\n"
            "Move the change into the spec, or rerun with --force to overwrite it."
        )
    if config.test_command and any(e.generated_files for e in hm.nodes.values()):
        passed, output = run_command(config.test_command)
        if not passed:
            raise BuildRefused(
                f"The test suite already fails before building:\n{output}\n"
                "Fix existing failures first so new failures can be traced to a spec."
            )


def execute_build(
    ordered_nodes: list[SpecNode],
    config: SpecdiffConfig,
    hm: HashMap,
    graph: SpecGraph,
    specs_dir: Path,
    *,
    review: bool = True,
    force: bool = False,
    inputs: dict[str, dict[str, str]] | None = None,
) -> BuildReport:
    """Build each node in order, saving it as soon as it passes its checks.

    A node that fails is rolled back on its own; nodes downstream of it are skipped.
    """
    preflight(ordered_nodes, config, hm, specs_dir, force)
    cfg = PipelineConfig(
        model=config.model,
        skills=load_build_skills(specs_dir),
        max_repairs=config.max_retries,
        review=review,
        test_command=config.test_command,
        check_command=config.check_command,
    )
    report = BuildReport()
    for node in ordered_nodes:
        blocked = {*report.failed, *report.skipped}
        if waiting := next((p for p in prerequisites(node) if p in blocked), None):
            report.skipped[node.id] = f"waits on {waiting}"
            click.echo(f"  [{node.id}] skipped: waits on {waiting}", err=True)
            continue
        _build_node(node, cfg, config, hm, graph, specs_dir, (inputs or {}).get(node.id), report)
    return report


def _build_node(node: SpecNode, cfg: PipelineConfig, config: SpecdiffConfig, hm: HashMap,
                graph: SpecGraph, specs_dir: Path, inputs: dict[str, str] | None,
                report: BuildReport) -> None:  # fmt: skip
    entry = hm.nodes.get(node.id)
    writer = NodeWriter(node, config.output_dir, specs_dir, entry.generated_files if entry else [])

    def log(message: str) -> None:
        click.echo(f"  [{node.id}] {message}")

    try:
        outcome = run_node(node_context(node.id, graph, hm, config), cfg, writer.sync, log)
    except click.ClickException:
        writer.rollback()
        raise
    except Exception as exc:
        writer.rollback()
        report.failed[node.id] = f"{type(exc).__name__}: {exc}"
        click.echo(f"  [{node.id}] failed: {exc}", err=True)
        return
    except BaseException:
        writer.rollback()
        raise

    report.usage += outcome.usage
    if not outcome.ok:
        writer.rollback()
        report.failed[node.id] = outcome.error
        click.echo(
            f"  [{node.id}] failed after {outcome.repairs} repair(s):\n{outcome.error}", err=True
        )
        return

    writer.commit()
    paths = [str(resolve_output_path(config.output_dir, rel)) for rel in outcome.files]
    hashmap.update(hm, node.id, node.hash, paths, inputs)
    hashmap.save(specs_dir, hm)
    report.built.append(node.id)
    u = outcome.usage
    click.echo(
        f"  [{node.id}] done: {len(paths)} file(s), {outcome.repairs} repair(s), "
        f"{u.calls} LLM call(s), {u.input_tokens:,} in / {u.output_tokens:,} out tokens"
    )
