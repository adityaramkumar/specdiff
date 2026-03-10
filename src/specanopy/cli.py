from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

from specanopy import hashmap
from specanopy.graph import build_graph, cascade, impact_summary
from specanopy.parser import discover_specs
from specanopy.runner import execute_cascade
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

    graph = build_graph(nodes)

    if node_id:
        if node_id not in graph.nodes:
            raise click.ClickException(f"Spec node '{node_id}' not found.")
        candidates = [graph.nodes[node_id]]
    else:
        candidates = nodes

    stale = [n for n in candidates if hashmap.is_stale(map, n.id, n.hash)]
    if not stale:
        click.echo("Everything is up to date.")
        return

    stale_ids = {n.id for n in nodes if hashmap.is_stale(map, n.id, n.hash)}
    ordered_ids = cascade(graph, [n.id for n in stale], stale_ids=stale_ids)
    ordered_nodes = [graph.nodes[nid] for nid in ordered_ids]

    click.echo(f"Building {len(ordered_nodes)} node(s)...\n")

    ok = execute_cascade(ordered_nodes, config, map, graph, specs_dir)
    hashmap.save(specs_dir, map)

    if not ok:
        sys.exit(1)
    click.echo("\nBuild complete.")


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


@cli.command()
@click.argument("node_id", required=False)
def impact(node_id: str | None) -> None:
    """Show the blast radius of pending spec changes."""
    config = _load_config(Path(".specanopy"))
    specs_dir = Path(config.specs_dir)
    map = hashmap.load(specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph = build_graph(nodes)

    stale = [n for n in nodes if hashmap.is_stale(map, n.id, n.hash)]
    if not stale:
        click.echo("Everything is up to date. No impact.")
        return

    if node_id:
        stale = [n for n in stale if n.id == node_id]
        if not stale:
            click.echo(f"Node '{node_id}' is not stale.")
            return

    summary = impact_summary(graph, [n.id for n in stale])

    click.echo("Stale spec nodes:")
    for nid in summary["changed"]:
        click.echo(f"  {nid}")

    if summary["downstream"]:
        click.echo("\nDownstream nodes affected:")
        for nid, depth in summary["downstream"].items():
            click.echo(f"  {nid:<35} (cascade depth {depth})")

    click.echo(f"\nTotal: {summary['total']} node(s) will be rebuilt")
