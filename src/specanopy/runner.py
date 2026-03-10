from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click

from specanopy import hashmap
from specanopy.generator import generate
from specanopy.types import HashMap, SpecNode, SpecanopyConfig

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


def execute(
    node: SpecNode,
    config: SpecanopyConfig,
    map: HashMap,
    specs_dir: Path,
) -> bool:
    """Full build cycle for a single spec node: generate -> test -> commit/rollback.

    Returns True on success, False on failure.
    """
    prev_entry = map.nodes.get(node.id)
    prev_files = prev_entry.generated_files if prev_entry else []

    backup(prev_files, specs_dir)

    try:
        written = generate(node, config)
    except Exception as exc:
        click.echo(f"  Generation failed: {exc}", err=True)
        restore(prev_files, specs_dir)
        return False

    passed, output = run_tests(config)

    if not passed:
        click.echo(f"  Tests failed for {node.id}, rolling back.", err=True)
        restore(written, specs_dir)
        return False

    clean_backups(specs_dir)
    hashmap.update(map, node.id, node.hash, written)
    return True
