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
        max_retries=raw.get("max_retries", SpecdiffConfig.max_retries),
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

    stale_ids = {n.id for n in nodes if hashmap.is_stale(hm, n.id, n.hash)}

    if node_id:
        if node_id not in graph.nodes:
            raise click.ClickException(f"Spec node '{node_id}' not found.")
        target = graph.nodes[node_id]
        # A targeted node must rebuild if it or any of its direct dependencies
        # are stale, even if its own hash hasn't changed.
        dep_stale = any(d in stale_ids for d in target.depends_on)
        if target.id in stale_ids or dep_stale:
            stale_ids.add(target.id)
        stale = [target] if target.id in stale_ids else []
    else:
        stale = [n for n in nodes if n.id in stale_ids]

    if not stale:
        click.echo("Everything is up to date.")
        return

    ordered_ids = cascade(graph, [n.id for n in stale], stale_ids=stale_ids)
    ordered_nodes = [graph.nodes[nid] for nid in ordered_ids]

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
max_retries: 2
"""
    (specs_dir / "config.yaml").write_text(config_yaml)

    skills = {
        SPEC_EVAL_SKILL: """\
You are a spec quality reviewer. Assess whether the spec is precise enough to
generate correct, unambiguous code from it without additional human input.

Return a JSON object:
  {"passed": true/false, "feedback": "...", "proposed_revision": "..." or null}

- passed: true only if the spec is fully self-contained and unambiguous.
- feedback: what is clear, and what (if anything) is vague or missing.
- proposed_revision: if passed is false, a revised markdown spec body that
  fixes all identified issues; otherwise null.
""",
        "architect": """\
You are the Architect agent. Analyse the spec and produce the file layout for
the implementation.

Output ONLY a valid JSON object mapping each relative file path to a one-line
description of that file's responsibility. No prose, no markdown fences.

Example:
{"auth/login.py": "Handles user login and returns a session token."}

Rules:
- Use the language and conventions stated in the prompt (.py, .ts, .go, etc.).
- Only include files strictly required by the spec.
- Keep paths relative to the output_dir (do not include the output_dir prefix).
""",
        "interface": """\
You are the Interface Planner agent. Given the spec and the architect's file
plan, define the precise public interface each file will expose.

Output ONLY a valid JSON object mapping each file path to its complete interface
definition as a string — function signatures, type annotations, class skeletons,
and module exports. No implementations. No prose outside the JSON.

Example:
{"auth/login.py": "def login(username: str, password: str) -> dict[str, str]: ..."}

Rules:
- Match the language and test framework stated in the prompt.
- Be exact: the Implementation agent will be held to these signatures.
- If dependency implementations are provided in the prompt, match their API exactly.
""",
        "implementation": """\
You are the Implementation agent. Given the spec, file plan, and interface
definitions, write the complete, working implementation for every file.

Output ONLY a valid JSON object mapping each file path to its complete file
contents as a string. No prose, no markdown fences around the JSON itself.

Rules:
- Satisfy EVERY requirement stated in the spec.
- Follow the exact signatures from the interface spec.
- Do NOT include any tests — only implementation code.
- If dependency implementations are provided, use their actual API exactly.
- If a review critique is provided, fix every issue it identifies.
""",
        "testing": """\
You are the Testing agent. Given the spec and interface definitions, write a
comprehensive test suite that verifies every requirement in the spec.

Output ONLY a valid JSON object mapping each test file path to its complete
contents as a string. Return an empty object {} if no tests are appropriate.

Rules:
- Cover the happy path, all error cases, and edge cases stated in the spec.
- Write tests against the interface spec — do not assume implementation details.
- Use the test framework stated in the prompt; default to pytest (Python) or
  vitest (TypeScript) if none is specified.
- Test file naming: tests/test_<module>.py (Python) or <module>.test.ts (TS).
""",
        "review": """\
You are the Review agent. Determine whether the generated implementation
faithfully satisfies every requirement in the spec.

Output ONLY a valid JSON object:
  {"passed": true/false, "feedback": "..."}

- passed: true only if ALL spec requirements are correctly implemented.
- feedback: summarise what was verified; if failed, list each missing or
  incorrect requirement with a specific, actionable description of the fix needed.

Be strict. A partial implementation must return passed: false.
""",
    }

    skills_dir = specs_dir / "skills"
    for name, content in skills.items():
        (skills_dir / f"{name}.skill.md").write_text(content)

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
