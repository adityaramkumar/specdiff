from __future__ import annotations

import sys

import click

from specdiff.agents.spec_agent import review_spec
from specdiff.build.runner import execute_build
from specdiff.cli.common import SPEC_EVAL_SKILL, load_states, project_config
from specdiff.parser import discover_specs
from specdiff.plan import plan_build
from specdiff.skills import legacy_skill_files, load_skill


@click.command()
@click.argument("node_id", required=False)
@click.option("--no-review", is_flag=True, help="Skip the LLM review stage")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be built without invoking any LLM",
)
@click.option("--force", is_flag=True, help="Overwrite generated files that were edited by hand")
def build(node_id: str | None, no_review: bool, dry_run: bool, force: bool) -> None:
    """Generate code for stale specs. With NODE_ID, build it and what it needs."""
    config, specs_dir = project_config()

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph, hm, states = load_states(config, specs_dir, nodes)
    if node_id and node_id not in graph.nodes:
        raise click.ClickException(f"Spec node '{node_id}' not found.")

    plan = plan_build(graph, states, node_id)
    for nid, why in plan.blocked.items():
        click.echo(f"  Skipping {nid} ({why})", err=True)

    if not plan.order:
        click.echo("Nothing to build." if plan.blocked else "Everything is up to date.")
        return

    ordered_nodes = [graph.nodes[nid] for nid in plan.order]

    if dry_run:
        click.echo(f"Would build {len(ordered_nodes)} node(s) in this order:\n")
        for i, nid in enumerate(plan.order, 1):
            why = ", ".join(states[nid].reasons) or "new"
            click.echo(f"  {i}. {nid}  [{why}]")
        return

    if config.review_before_build:
        try:
            skill = load_skill(specs_dir, SPEC_EVAL_SKILL)
        except FileNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

        for node in ordered_nodes:
            click.echo(f"  Reviewing {node.id}...")
            result = review_spec(node, skill, config)
            if not result.passed:
                click.echo(f"\n  Review failed for {node.id}:")
                click.echo(f"  {result.feedback}")
                raise click.ClickException(
                    f"Spec '{node.id}' failed review. Run `specdiff review` to see suggestions."
                )

    for path in legacy_skill_files(specs_dir):
        click.echo(
            f"  Note: {path} is no longer used. Build skills are now plan, implement, test, "
            "repair and review; see `specdiff init` for how to override them.",
            err=True,
        )

    click.echo(f"Building {len(ordered_nodes)} node(s)...\n")
    report = execute_build(
        ordered_nodes,
        config,
        hm,
        graph,
        specs_dir,
        review=not no_review,
        force=force,
        inputs={nid: states[nid].inputs for nid in plan.order},
    )

    u = report.usage
    click.echo(
        f"\nBuilt {len(report.built)}, failed {len(report.failed)}, skipped "
        f"{len(report.skipped)}. {u.calls} LLM call(s), {u.input_tokens:,} in / "
        f"{u.output_tokens:,} out tokens."
    )
    if not report.ok:
        sys.exit(1)
