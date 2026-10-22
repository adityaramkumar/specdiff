from __future__ import annotations

import sys
from pathlib import Path

import click
import frontmatter
from dotenv import load_dotenv

from specdiff import hashmap
from specdiff.agents.spec_agent import review_spec
from specdiff.build.runner import execute_build
from specdiff.config import load_config
from specdiff.graph import SpecGraph, build_graph, impact_summary
from specdiff.parser import discover_specs
from specdiff.plan import NodeState, compute_states, plan_build, skills_hash
from specdiff.skills import legacy_skill_files, load_skill
from specdiff.types import HashMap, SpecdiffConfig

SPEC_EVAL_SKILL = "spec-eval"


def _load_graph(nodes) -> SpecGraph:
    try:
        return build_graph(nodes)
    except ValueError as exc:
        raise click.ClickException(f"{exc}\nRun `specdiff validate` to see every problem.") from exc


def _load_states(
    config: SpecdiffConfig, specs_dir: Path, nodes
) -> tuple[SpecGraph, HashMap, dict[str, NodeState]]:
    graph = _load_graph(nodes)
    hm = hashmap.load(specs_dir)
    return graph, hm, compute_states(graph, hm, config, skills_hash(specs_dir))


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
@click.option("--no-review", is_flag=True, help="Skip the LLM review stage")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be built without invoking any LLM",
)
@click.option("--force", is_flag=True, help="Overwrite generated files that were edited by hand")
def build(node_id: str | None, no_review: bool, dry_run: bool, force: bool) -> None:
    """Generate code for stale specs. With NODE_ID, build it and what it needs."""
    config = load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph, hm, states = _load_states(config, specs_dir, nodes)
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


@cli.command()
def status() -> None:
    """Show which specs are current, stale, or new, and why."""
    config = load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph, hm, states = _load_states(config, specs_dir, nodes)

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


@cli.command()
def validate() -> None:
    """Check the spec graph for errors before building.

    Verifies that all depends_on and parent references resolve, that there
    are no duplicate node IDs, and that no circular dependencies exist.
    Exits with code 1 if any errors are found.
    """
    config = load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

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


@cli.command()
@click.argument("node_id", required=False)
def impact(node_id: str | None) -> None:
    """Show what a build would touch.

    With NODE_ID, show every spec downstream of it: the blast radius of changing it.
    """
    config = load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    nodes = discover_specs(specs_dir)
    if not nodes:
        click.echo("No spec files found.")
        return

    graph, _, states = _load_states(config, specs_dir, nodes)

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


@cli.command()
@click.argument("node_id", required=False)
def review(node_id: str | None) -> None:
    """Review specs for quality. Optionally target a single NODE_ID."""
    config = load_config(Path(".specdiff"))
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
    config = load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)

    # We delay this import to avoid circular dependency if `api` imports from `cli`
    from specdiff.api import serve_ui

    serve_ui(specs_dir, port=port, open_browser=not no_browser)


INIT_CONFIG = """\
# Model prefixes: gemini-* (GEMINI_API_KEY), claude-* (ANTHROPIC_API_KEY),
# gpt-*/o* (OPENAI_API_KEY), grok-* (XAI_API_KEY).
model: gemini-2.5-flash
output_dir: src
specs_dir: .specdiff
language: python
test_framework: pytest
# Run after every spec is generated; failures are fed back to the repair stage.
test_command: PYTHONPATH=src python -m pytest -q src
# Optional extra check, e.g. a typechecker: check_command: npx tsc --noEmit
review_before_build: false
# Repair attempts per spec when a check fails.
max_retries: 2
"""

SKILLS_README = """\
# Skills

Each build stage runs with a built-in prompt ("skill"): plan, implement, test,
repair, review, plus spec-eval for `specdiff review`.

To customise one, print the built-in version into this folder and edit it:

    specdiff skill implement > .specdiff/skills/implement.skill.md

A file here replaces the built-in skill. Changing a build skill marks every spec
stale, since it changes what the generated code would be.
"""

EXAMPLE_SPEC = """\
---
id: behaviors/hello
version: "1.0.0"
status: approved
---

## Hello World

Replace this with your first real spec.

### Acceptance Criteria

- `greet(name)` returns "Hello, <name>!"
- If name is empty or only whitespace, it returns "Hello, World!"
- Name is stripped of leading and trailing whitespace before use
"""


@cli.command()
def init() -> None:
    """Initialize a .specdiff directory with a config and an example spec."""
    specs_dir = Path(".specdiff")
    if specs_dir.exists():
        click.echo(f"Directory {specs_dir} already exists.")
        return

    (specs_dir / "skills").mkdir(parents=True)
    (specs_dir / "behaviors").mkdir()
    (specs_dir / "config.yaml").write_text(INIT_CONFIG)
    (specs_dir / "skills" / "README.md").write_text(SKILLS_README)
    (specs_dir / "behaviors" / "hello.spec.md").write_text(EXAMPLE_SPEC)
    click.echo("Created .specdiff/ with config.yaml and behaviors/hello.spec.md.")
    click.echo("Set your model's API key, then run `specdiff build`.")


@cli.command()
@click.argument("name")
def skill(name: str) -> None:
    """Print the skill NAME as the build uses it (your override or the built-in)."""
    try:
        click.echo(load_skill(Path(load_config(Path(".specdiff")).specs_dir), name), nl=False)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument("node_id", required=False)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def clean(node_id: str | None, yes: bool) -> None:
    """Delete generated files and remove them from the hash map.

    Forces a full rebuild of NODE_ID (or all nodes) on the next build.
    """
    config = load_config(Path(".specdiff"))
    specs_dir = Path(config.specs_dir)
    hm = hashmap.load(specs_dir)

    if not hm.nodes:
        click.echo("Nothing to clean.")
        return

    if node_id:
        if node_id not in hm.nodes:
            raise click.ClickException(f"Node '{node_id}' has no tracked generated files.")
        targets = {node_id: hm.nodes[node_id]}
    else:
        targets = dict(hm.nodes)

    edited = [f for e in targets.values() for f in hashmap.modified_files(e)]
    if edited:
        click.echo("Warning: these generated files were edited by hand and will be deleted:")
        for f in edited:
            click.echo(f"  {f}")

    total_files = sum(len(e.generated_files) for e in targets.values())
    prompt = f"Remove {len(targets)} node(s) and {total_files} generated file(s) from the hash map?"
    if not yes and not click.confirm(prompt):
        click.echo("Aborted.")
        return

    for nid, entry in targets.items():
        removed = 0
        for path_str in entry.generated_files:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                removed += 1
        del hm.nodes[nid]
        click.echo(f"  [{nid}] cleaned ({removed} file(s) removed)")

    hashmap.save(specs_dir, hm)
    click.echo("\nClean complete.")


@cli.command()
@click.option("--source", default=".", help="Directory to read code from")
@click.option("--granularity", default="auto", help="Extraction granularity ('auto' or 'file')")
def extract(source: str, granularity: str) -> None:
    """Read existing code and generate spec files."""
    config = load_config(Path(".specdiff"))
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
