from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click

from specanopy import hashmap
from specanopy.agents.swarm import run_swarm
from specanopy.graph import SpecGraph
from specanopy.types import HashMap, SpecanopyConfig, SpecNode

BACKUP_DIR = ".backup"


def backup(files: list[str], specs_dir: Path) -> None:
    """Copy existing generated files into .specanopy/.backup/ before overwriting."""
    backup_root = specs_dir / BACKUP_DIR
    for rel in files:
        src = Path(rel)
        if not src.exists():
            continue
        dest = backup_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def restore(files: list[str], specs_dir: Path) -> None:
    """Restore backed-up files to their original locations."""
    backup_root = specs_dir / BACKUP_DIR
    for rel in files:
        backed = backup_root / rel
        if not backed.exists():
            Path(rel).unlink(missing_ok=True)
            continue
        dest = Path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backed, dest)
    clean_backups(specs_dir)


def clean_backups(specs_dir: Path) -> None:
    """Remove the entire .specanopy/.backup/ directory."""
    backup_root = specs_dir / BACKUP_DIR
    if backup_root.exists():
        shutil.rmtree(backup_root)


def run_tests(config: SpecanopyConfig) -> tuple[bool, str]:
    """Run the configured test command. Returns (passed, output).

    stdout/stderr stream live to the terminal so the user sees progress.
    """
    if not config.test_command:
        return True, ""

    result = subprocess.run(
        config.test_command,
        shell=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    click.echo(output, nl=False)
    return result.returncode == 0, output


TRACEABILITY_TEMPLATE = (
    "# generated_from: {node_id}\n"
    "# spec_hash: {spec_hash}\n"
    "# generated_at: {timestamp}\n"
    "# agent: {agent}\n"
)


def _write_swarm_files(
    files: dict[str, str],
    output_dir: str,
    node: SpecNode,
    agent_name: str,
) -> list[str]:
    """Write generated files to disk with traceability headers."""
    header = TRACEABILITY_TEMPLATE.format(
        node_id=node.id,
        spec_hash=node.hash,
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent=agent_name,
    )
    written: list[str] = []
    for rel_path, contents in files.items():
        full_path = Path(output_dir) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(header + "\n" + contents, "utf-8")
        written.append(str(full_path))
    return written


def execute_swarm_cascade(
    ordered_nodes: list[SpecNode],
    config: SpecanopyConfig,
    map: HashMap,
    graph: SpecGraph,
    specs_dir: Path,
) -> bool:
    """Build nodes using the multi-agent swarm pipeline."""
    if config.test_command:
        baseline_ok, _ = run_tests(config)
        if not baseline_ok:
            click.echo(
                "  Test suite is already failing -- fix existing failures before regenerating.",
                err=True,
            )
            return False

    all_prev_files: list[str] = []
    for node in ordered_nodes:
        entry = map.nodes.get(node.id)
        if entry:
            all_prev_files.extend(entry.generated_files)

    backup(all_prev_files, specs_dir)

    all_written: dict[str, list[str]] = {}
    for node in ordered_nodes:
        click.echo(f"  [{node.id}] running swarm...")
        dep_specs = [graph.nodes[d] for d in node.depends_on if d in graph.nodes]
        try:
            result = run_swarm(node, config, specs_dir, dep_specs=dep_specs)
        except Exception as exc:
            click.echo(f"  [{node.id}] swarm failed: {exc}", err=True)
            all_restore = [f for files in all_written.values() for f in files]
            restore(all_restore + all_prev_files, specs_dir)
            return False

        written = _write_swarm_files(
            result.generated_files, config.output_dir, node, "implementation-agent"
        )
        written += _write_swarm_files(
            result.generated_tests, config.output_dir, node, "testing-agent"
        )
        all_written[node.id] = written

        if not result.review_passed:
            click.echo(f"  [{node.id}] review warning: {result.review_feedback}")
        click.echo(f"  [{node.id}] done.")

    passed, _ = run_tests(config)

    if not passed:
        click.echo("  Tests failed, rolling back entire cascade.", err=True)
        all_new = [f for files in all_written.values() for f in files]
        restore(all_new + all_prev_files, specs_dir)
        return False

    clean_backups(specs_dir)
    for node in ordered_nodes:
        hashmap.update(map, node.id, node.hash, all_written[node.id])
    return True
