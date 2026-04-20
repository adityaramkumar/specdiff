from __future__ import annotations

import contextlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click

from specdiff import hashmap
from specdiff.agents.swarm import run_swarm
from specdiff.graph import SpecGraph
from specdiff.types import HashMap, SpecdiffConfig, SpecNode, SwarmResult

BACKUP_DIR = ".backup"


def backup(files: list[str], specs_dir: Path) -> None:
    """Copy existing generated files into .specdiff/.backup/ before overwriting."""
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
    """Remove the entire .specdiff/.backup/ directory."""
    backup_root = specs_dir / BACKUP_DIR
    if backup_root.exists():
        shutil.rmtree(backup_root)


def run_tests(config: SpecdiffConfig) -> tuple[bool, str]:
    """Run the configured test command. Returns (passed, combined output)."""
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


def _line_comment_header(prefix: str, metadata: dict[str, str]) -> str:
    return "\n".join(f"{prefix} {key}: {value}" for key, value in metadata.items())


def _block_comment_header(start: str, end: str, metadata: dict[str, str]) -> str:
    lines = [start]
    lines.extend(f"  {key}: {value}" for key, value in metadata.items())
    lines.append(end)
    return "\n".join(lines)


def _traceability_header(path: Path, node: SpecNode, agent_name: str) -> str:
    metadata = {
        "generated_from": node.id,
        "spec_hash": node.hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
    }
    ext = path.suffix.lower()

    if ext in {".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".c", ".cc", ".cpp"}:
        return _line_comment_header("//", metadata)
    if ext in {".css", ".scss", ".less", ".sql"}:
        return _block_comment_header("/*", "*/", metadata)
    if ext in {".html", ".xml", ".svg", ".md"}:
        return _block_comment_header("<!--", "-->", metadata)

    return _line_comment_header("#", metadata)


def _write_swarm_files(
    files: dict[str, str],
    output_dir: str,
    node: SpecNode,
    agent_name: str,
) -> list[str]:
    """Write generated files to disk with traceability headers."""
    written: list[str] = []
    for rel_path, contents in files.items():
        full_path = Path(output_dir) / rel_path
        header = _traceability_header(full_path, node, agent_name)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(header + "\n" + contents, "utf-8")
        written.append(str(full_path))
    return written


def execute_swarm_cascade(
    ordered_nodes: list[SpecNode],
    config: SpecdiffConfig,
    hm: HashMap,
    graph: SpecGraph,
    specs_dir: Path,
    *,
    skip_review: bool = False,
) -> bool:
    """Build nodes using the multi-agent swarm pipeline."""
    has_existing_files = any(entry.generated_files for entry in hm.nodes.values())
    if config.test_command and has_existing_files:
        baseline_ok, _ = run_tests(config)
        if not baseline_ok:
            click.echo(
                "  Test suite is already failing -- fix existing failures before regenerating.",
                err=True,
            )
            return False

    all_prev_files: list[str] = []
    for node in ordered_nodes:
        entry = hm.nodes.get(node.id)
        if entry:
            all_prev_files.extend(entry.generated_files)

    backup(all_prev_files, specs_dir)

    all_written: dict[str, list[str]] = {}
    for node in ordered_nodes:
        click.echo(f"  [{node.id}] running swarm...")
        dep_specs = [graph.nodes[d] for d in node.depends_on if d in graph.nodes]

        # Include the actual generated code for each dependency so the
        # implementation agent sees real API shapes, not just the spec prose.
        dep_generated: dict[str, str] = {}
        for dep_id in node.depends_on:
            dep_entry = hm.nodes.get(dep_id)
            if dep_entry:
                for file_path in dep_entry.generated_files:
                    with contextlib.suppress(FileNotFoundError):
                        dep_generated[file_path] = Path(file_path).read_text("utf-8")

        result: SwarmResult | None = None
        prior_critique: str | None = None
        max_attempts = config.max_retries + 1
        for attempt in range(max_attempts):
            if attempt > 0:
                click.echo(
                    f"  [{node.id}] review failed, retrying ({attempt}/{config.max_retries})..."
                )
            try:
                result = run_swarm(
                    node,
                    config,
                    specs_dir,
                    dep_specs=dep_specs,
                    dep_generated=dep_generated or None,
                    prior_critique=prior_critique,
                )
            except Exception as exc:
                click.echo(f"  [{node.id}] swarm failed: {exc}", err=True)
                all_restore = [f for files in all_written.values() for f in files]
                restore(all_restore + all_prev_files, specs_dir)
                return False

            if result.review_passed:
                break
            prior_critique = result.review_feedback

        if result is None:
            raise RuntimeError(
                f"[{node.id}] swarm produced no result after {max_attempts} attempt(s)."
            )

        if result.generated_tests and not config.test_command:
            click.echo(
                f"  [{node.id}] generated tests but no test_command is configured.",
                err=True,
            )
            click.echo(
                "  Set test_command in .specdiff/config.yaml so Specdiff can run a baseline "
                "and verify regenerated output.",
                err=True,
            )
            all_restore = [f for files in all_written.values() for f in files]
            restore(all_restore + all_prev_files, specs_dir)
            return False

        if not result.review_passed:
            if skip_review:
                click.echo(
                    f"  [{node.id}] review failed after {max_attempts} attempt(s)"
                    f" (--no-review, continuing): {result.review_feedback}",
                )
            else:
                click.echo(
                    f"  [{node.id}] review failed after {max_attempts} attempt(s): "
                    f"{result.review_feedback}",
                    err=True,
                )
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
        n = len(written)
        click.echo(f"  [{node.id}] done. ({n} file{'s' if n != 1 else ''} written)")

    passed, _ = run_tests(config)

    if not passed:
        click.echo("  Tests failed, rolling back entire cascade.", err=True)
        all_new = [f for files in all_written.values() for f in files]
        restore(all_new + all_prev_files, specs_dir)
        return False

    clean_backups(specs_dir)

    # Delete files that were generated by a previous build but are no longer
    # in the new file plan (architect changed paths between runs).
    for node in ordered_nodes:
        old_entry = hm.nodes.get(node.id)
        if old_entry:
            new_files = set(all_written.get(node.id, []))
            for stale_path in old_entry.generated_files:
                if stale_path not in new_files:
                    Path(stale_path).unlink(missing_ok=True)

    for node in ordered_nodes:
        hashmap.update(hm, node.id, node.hash, all_written[node.id])
    return True
