from __future__ import annotations

import sys
from pathlib import Path

import click
import frontmatter
import yaml
from dotenv import load_dotenv

from specdiff import hashmap
from specdiff.agents.spec_agent import review_spec
from specdiff.graph import build_graph, cascade, impact_summary
from specdiff.parser import discover_specs
from specdiff.runner import execute_swarm_cascade
from specdiff.skills import load_skill
from specdiff.types import SpecdiffConfig

SPEC_EVAL_SKILL = "spec-eval"


def _load_config(specs_dir: Path) -> SpecdiffConfig:
    config_path = specs_dir / "config.yaml"
    if not config_path.exists():
        return SpecdiffConfig()
    raw = yaml.safe_load(config_path.read_text("utf-8")) or {}
    return SpecdiffConfig(
        model=raw.get("model", SpecdiffConfig.model),
        test_command=raw.get("test_command"),
        output_dir=raw.get("output_dir", SpecdiffConfig.output_dir),
        specs_dir=raw.get("specs_dir", SpecdiffConfig.specs_dir),
        review_before_build=raw.get("review_before_build", False),
        language=raw.get("language", SpecdiffConfig.language),
        test_framework=raw.get("test_framework"),
    )


def _update_spec_status(file_path: str, new_status: str) -> None:
    """Update the status field in a spec file's frontmatter."""
    post = frontmatter.load(file_path)
    post.metadata["status"] = new_status
    Path(file_path).write_text(frontmatter.dumps(post), "utf-8")


def _write_proposed_revision(
    specs_dir: Path, node_id: str, revision: str, original_path: str
) -> Path:
    """Write a proposed revision spec to .specdiff/proposed/."""
    proposed_dir = specs_dir / "proposed"
    proposed_path = proposed_dir / f"{node_id.replace('/', '_')}.spec.md"
    proposed_path.parent.mkdir(parents=True, exist_ok=True)

    original = frontmatter.load(original_path)
    original.content = revision
    proposed_path.write_text(frontmatter.dumps(original), "utf-8")
    return proposed_path


@click.group()
def cli() -> None:
    """Specdiff — spec-driven code generation."""
    load_dotenv()


@cli.command()
@click.argument("node_id", required=False)
@click.option("--no-review", is_flag=True, help="Skip the review gate")
def build(node_id: str | None, no_review: bool) -> None:
    """Generate code from specs. Optionally target a single NODE_ID."""
    config = _load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)
    hm = hashmap.load(specs_dir)

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

    stale = [n for n in candidates if hashmap.is_stale(hm, n.id, n.hash)]
    if not stale:
        click.echo("Everything is up to date.")
        return

    if config.review_before_build:
        try:
            skill = load_skill(specs_dir, SPEC_EVAL_SKILL)
        except FileNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

        for node in stale:
            click.echo(f"  Reviewing {node.id}...")
            result = review_spec(node, skill, config)
            if not result.passed:
                click.echo(f"\n  Review failed for {node.id}:")
                click.echo(f"  {result.feedback}")
                raise click.ClickException(
                    f"Spec '{node.id}' failed review. Run `specdiff review` to see suggestions."
                )

    stale_ids = {n.id for n in nodes if hashmap.is_stale(hm, n.id, n.hash)}
    ordered_ids = cascade(graph, [n.id for n in stale], stale_ids=stale_ids)
    ordered_nodes = [graph.nodes[nid] for nid in ordered_ids]

    click.echo(f"Building {len(ordered_nodes)} node(s)...\n")

    ok = execute_swarm_cascade(ordered_nodes, config, hm, graph, specs_dir, skip_review=no_review)

    if not ok:
        sys.exit(1)
    hashmap.save(specs_dir, hm)
    click.echo("\nBuild complete.")


@cli.command()
def status() -> None:
    """Show staleness status for all spec nodes."""
    config = _load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)
    hm = hashmap.load(specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    click.echo(f"{'Node ID':<35} {'Status':<10} {'Version'}")
    click.echo("-" * 60)

    for node in nodes:
        entry = hm.nodes.get(node.id)
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
    config = _load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)
    hm = hashmap.load(specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph = build_graph(nodes)

    stale = [n for n in nodes if hashmap.is_stale(hm, n.id, n.hash)]
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


@cli.command()
@click.argument("node_id", required=False)
def review(node_id: str | None) -> None:
    """Review specs for quality. Optionally target a single NODE_ID."""
    config = _load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    try:
        skill = load_skill(specs_dir, SPEC_EVAL_SKILL)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    if node_id:
        nodes = [n for n in nodes if n.id == node_id]
        if not nodes:
            raise click.ClickException(f"Spec node '{node_id}' not found.")
    else:
        nodes = [n for n in nodes if n.status != "approved"]
        if not nodes:
            click.echo("All specs are already approved.")
            return

    any_failed = False
    for node in nodes:
        click.echo(f"Reviewing {node.id}...")
        result = review_spec(node, skill, config)

        if result.passed:
            click.echo(f"  PASSED: {result.feedback}\n")
            _update_spec_status(node.file_path, "approved")
        else:
            any_failed = True
            click.echo(f"  FAILED: {result.feedback}\n")
            if result.proposed_revision:
                path = _write_proposed_revision(
                    specs_dir, node.id, result.proposed_revision, node.file_path
                )
                click.echo(
                    f"  Suggested revision written to:\n"
                    f"    {path}\n\n"
                    f"  Review the suggested changes. If they capture your intent,\n"
                    f"  copy them to your spec and run `specdiff review` again.\n"
                )

    if any_failed:
        sys.exit(1)


@cli.command()
@click.option("--port", default=8000, help="Port to run the UI server on")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically")
def ui(port: int, no_browser: bool) -> None:
    """Launch the interactive graphical UI in your browser."""
    config = _load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    # We delay this import to avoid circular dependency if `api` imports from `cli`
    from specdiff.api import serve_ui

    serve_ui(specs_dir, port=port, open_browser=not no_browser)


@cli.command()
def init() -> None:
    """Initialize a .specdiff directory with a default config."""
    specs_dir = Path(".specdiff")
    if specs_dir.exists():
        click.echo(f"Directory {specs_dir} already exists.")
        return

    specs_dir.mkdir()
    (specs_dir / "skills").mkdir()

    config_yaml = """model: gemini-2.5-flash
# For xAI: model: grok-4-1-fast-non-reasoning
output_dir: src
specs_dir: .specdiff
language: python
review_before_build: false
"""
    (specs_dir / "config.yaml").write_text(config_yaml)

    # Placeholder skill
    skill_content = """# spec-eval.skill.md
Ensure the spec is completely unambiguous.
"""
    (specs_dir / "skills" / f"{SPEC_EVAL_SKILL}.skill.md").write_text(skill_content)

    click.echo("Initialized empty specdiff project in .specdiff/")


@cli.command()
@click.option("--source", default=".", help="Directory to read code from")
@click.option("--granularity", default="auto", help="Extraction granularity ('auto' or 'file')")
def extract(source: str, granularity: str) -> None:
    """Read existing code and generate spec files."""
    config = _load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    if not specs_dir.exists():
        click.echo("Specdiff not initialized. Please run `specdiff init` first.")
        return

    src_path = Path(source)
    if not src_path.exists():
        click.echo(f"Source directory {source} does not exist.")
        sys.exit(1)

    # Delay import so we don't load the LLM unless the command is run
    from specdiff.extract import generate_specs_from_code

    generate_specs_from_code(src_path, specs_dir, config, granularity)
