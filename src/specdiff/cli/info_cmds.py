from __future__ import annotations

import sys
from pathlib import Path

import click

from specdiff import hashmap
from specdiff.cli.common import load_states, project_config
from specdiff.graph import build_graph, impact_summary
from specdiff.parser import discover_specs
from specdiff.plan import plan_build


@click.command()
def status() -> None:
    """Show which specs are current, stale, or new, and why."""
    config, specs_dir = project_config()

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph, hm, states = load_states(config, specs_dir, nodes)

    click.echo(f"{'Node ID':<35} {'Status':<10} {'Version':<10} Why")
    click.echo("-" * 80)
    for node in nodes:
        state = states[node.id]
        why = ", ".join(state.reasons)
        if node.status == "draft":
            why = f"draft; {why}" if why else "draft"
        click.echo(f"{node.id:<35} {state.label:<10} {node.version:<10} {why}".rstrip())

    edited = [f for e in hm.nodes.values() for f in hashmap.modified_files(e)]
    if edited:
        click.echo("\nGenerated files edited by hand (build needs --force to overwrite):")
        for f in edited:
            click.echo(f"  {f}")


@click.command()
def validate() -> None:
    """Check the spec graph for errors before building.

    Verifies that all depends_on and parent references resolve, that there
    are no duplicate node IDs, and that no circular dependencies exist.
    Exits with code 1 if any errors are found.
    """
    config, specs_dir = project_config()

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    node_map = {n.id: n for n in nodes}
    errors: list[str] = []

    seen_ids: dict[str, str] = {}
    for node in nodes:
        if node.id in seen_ids:
            errors.append(f"  Duplicate ID '{node.id}': {node.file_path} and {seen_ids[node.id]}")
        else:
            seen_ids[node.id] = node.file_path

    for node in nodes:
        for dep_id in node.depends_on:
            if dep_id not in node_map:
                errors.append(f"  {node.id}: depends_on '{dep_id}' not found")

    for node in nodes:
        if node.parent and node.parent not in node_map:
            errors.append(f"  {node.id}: parent '{node.parent}' not found")

    for node in nodes:
        for path in node.acceptance:
            if not Path(path).is_file():
                errors.append(f"  {node.id}: acceptance test '{path}' not found")

    if not errors:
        try:
            build_graph(nodes)
        except ValueError as exc:
            errors.append(f"  {exc}")

    if errors:
        click.echo(f"Found {len(errors)} error(s):\n")
        for err in errors:
            click.echo(err)
        sys.exit(1)
    else:
        click.echo(f"Validated {len(nodes)} spec(s). No issues found.")


@click.command()
@click.argument("node_id", required=False)
def impact(node_id: str | None) -> None:
    """Show what a build would touch.

    With NODE_ID, show every spec downstream of it: the blast radius of changing it.
    """
    config, specs_dir = project_config()

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph, _, states = load_states(config, specs_dir, nodes)

    if node_id:
        if node_id not in graph.nodes:
            raise click.ClickException(f"Spec node '{node_id}' not found.")
        summary = impact_summary(graph, [node_id])
        if not summary["downstream"]:
            click.echo(f"Nothing depends on {node_id}.")
            return
        click.echo(f"Changing {node_id} rebuilds:")
        for nid, depth in summary["downstream"].items():
            click.echo(f"  {nid:<35} (cascade depth {depth})")
        click.echo(f"\nTotal: {summary['total']} node(s)")
        return

    stale = [nid for nid in plan_build(graph, states).order]
    if not stale:
        click.echo("Everything is up to date. No impact.")
        return
    click.echo("Stale spec nodes, in build order:")
    for nid in stale:
        why = ", ".join(states[nid].reasons) or "new"
        click.echo(f"  {nid:<35} {why}")
    click.echo(f"\nTotal: {len(stale)} node(s) will be rebuilt")
