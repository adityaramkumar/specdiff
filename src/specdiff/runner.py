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


def _backup_path(backup_root: Path, rel: str) -> Path:
    path = Path(rel)
    return backup_root / path.relative_to(path.anchor) if path.is_absolute() else backup_root / path


def backup(files: list[str], specs_dir: Path) -> None:
    """Copy existing files into .specdiff/.backup/ before overwriting.

    A file that already has a backup keeps it, so the backup always holds the
    pre-build original even when several nodes in a cascade write the same path.
    """
    backup_root = specs_dir / BACKUP_DIR
    for rel in files:
        src = Path(rel)
        dest = _backup_path(backup_root, rel)
        if not src.exists() or dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def restore(files: list[str], specs_dir: Path) -> None:
    """Restore backed-up files to their original locations."""
    backup_root = specs_dir / BACKUP_DIR
    for rel in files:
        backed = _backup_path(backup_root, rel)
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


def resolve_output_path(output_dir: str, rel_path: str) -> Path:
    """Join an agent-supplied path onto output_dir, rejecting anything that escapes it."""
    root = Path(output_dir).resolve()
    if not (root / rel_path).resolve().is_relative_to(root):
        raise ValueError(f"Generated path {rel_path!r} escapes output_dir {output_dir!r}.")
    return Path(output_dir) / rel_path


def _write_swarm_files(
    files: dict[str, Path],
    contents: dict[str, str],
    node: SpecNode,
    agent_name: str,
) -> None:
    """Write generated files to disk with traceability headers."""
    for rel_path, full_path in files.items():
        header = _traceability_header(full_path, node, agent_name)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(header + "\n" + contents[rel_path], "utf-8")


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
    if (specs_dir / BACKUP_DIR).exists():
        click.echo(
            f"  {specs_dir / BACKUP_DIR} exists from an interrupted build. Copy back any "
            "files you need from it, then delete it before building again.",
            err=True,
        )
        return False

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

    def rollback() -> None:
        restore([f for files in all_written.values() for f in files] + all_prev_files, specs_dir)

    try:
        if not _build_nodes(ordered_nodes, config, hm, graph, specs_dir, all_written, skip_review):
            rollback()
            return False

        passed, _ = run_tests(config)
        if not passed:
            click.echo("  Tests failed, rolling back entire cascade.", err=True)
            rollback()
            return False
    except BaseException:
        click.echo("  Build interrupted, rolling back.", err=True)
        rollback()
        raise

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


def _build_nodes(
    ordered_nodes: list[SpecNode],
    config: SpecdiffConfig,
    hm: HashMap,
    graph: SpecGraph,
    specs_dir: Path,
    all_written: dict[str, list[str]],
    skip_review: bool,
) -> bool:
    """Run the swarm for each node and write its output. Returns False on failure."""
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
                return False

        try:
            code_paths = {
                rel: resolve_output_path(config.output_dir, rel) for rel in result.generated_files
            }
            test_paths = {
                rel: resolve_output_path(config.output_dir, rel) for rel in result.generated_tests
            }
        except ValueError as exc:
            click.echo(f"  [{node.id}] {exc}", err=True)
            return False

        targets = [str(p) for p in [*code_paths.values(), *test_paths.values()]]
        # Back up hand-written files too, not just ones a previous build produced,
        # and record targets before writing so an interrupted write is rolled back.
        backup(targets, specs_dir)
        all_written[node.id] = targets
        _write_swarm_files(code_paths, result.generated_files, node, "implementation-agent")
        _write_swarm_files(test_paths, result.generated_tests, node, "testing-agent")
        n = len(targets)
        click.echo(f"  [{node.id}] done. ({n} file{'s' if n != 1 else ''} written)")

    return True
