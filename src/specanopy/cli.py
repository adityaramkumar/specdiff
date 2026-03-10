from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

from specanopy import hashmap
from specanopy.parser import discover_specs
from specanopy.runner import execute
from specanopy.types import SpecanopyConfig


def _load_config(specs_dir: Path) -> SpecanopyConfig:
    config_path = specs_dir / "config.yaml"
    if not config_path.exists():
        return SpecanopyConfig()
    raw = yaml.safe_load(config_path.read_text("utf-8")) or {}
    return SpecanopyConfig(
        model=raw.get("model", SpecanopyConfig.model),
        test_command=raw.get("test_command"),
        output_dir=raw.get("output_dir", SpecanopyConfig.output_dir),
        specs_dir=raw.get("specs_dir", SpecanopyConfig.specs_dir),
    )


@click.group()
def cli() -> None:
    """Specanopy — spec-driven code generation."""
    load_dotenv()


@cli.command()
@click.argument("node_id", required=False)
def build(node_id: str | None) -> None:
    """Generate code from specs. Optionally target a single NODE_ID."""
    config = _load_config(Path(".specanopy"))
    specs_dir = Path(config.specs_dir)
    map = hashmap.load(specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    if node_id:
        nodes = [n for n in nodes if n.id == node_id]
        if not nodes:
            raise click.ClickException(f"Spec node '{node_id}' not found.")

    stale = [n for n in nodes if hashmap.is_stale(map, n.id, n.hash)]
    if not stale:
        click.echo("Everything is up to date.")
        return

    click.echo(f"Building {len(stale)} stale node(s)...\n")
    failed = False

    for node in stale:
        click.echo(f"  [{node.id}] generating...")
        ok = execute(node, config, map, specs_dir)
        if ok:
            click.echo(f"  [{node.id}] done.\n")
        else:
            click.echo(f"  [{node.id}] FAILED.\n", err=True)
            failed = True

    hashmap.save(specs_dir, map)

    if failed:
        sys.exit(1)
    click.echo("Build complete.")


@cli.command()
def status() -> None:
    """Show staleness status for all spec nodes."""
    config = _load_config(Path(".specanopy"))
    specs_dir = Path(config.specs_dir)
    map = hashmap.load(specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    click.echo(f"{'Node ID':<35} {'Status':<10} {'Version'}")
    click.echo("-" * 60)

    for node in nodes:
        entry = map.nodes.get(node.id)
        if entry is None:
            label = "new"
        elif entry.spec_hash != node.hash:
            label = "stale"
        else:
            label = "current"
        click.echo(f"{node.id:<35} {label:<10} {node.version}")
