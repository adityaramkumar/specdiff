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
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be built without invoking any LLM",
)
def build(node_id: str | None, no_review: bool, dry_run: bool) -> None:
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

    if dry_run:
        click.echo(f"Would build {len(ordered_nodes)} node(s) in this order:\n")
        for i, node in enumerate(ordered_nodes, 1):
            reason = "stale" if node.id in stale_ids else "cascade"
            deps_str = ""
            if node.depends_on:
                deps_str = f", depends on {', '.join(node.depends_on)}"
            click.echo(f"  {i}. {node.id}  [{reason}{deps_str}]")
        return

    for node in ordered_nodes:
        for dep_id in node.depends_on:
            if dep_id not in graph.nodes:
                click.echo(
                    f"  Warning: '{node.id}' depends on '{dep_id}' which was not found.\n"
                    f"  Create '.specdiff/{dep_id}.spec.md' to provide dependency context.",
                    err=True,
                )

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
def validate() -> None:
    """Check the spec graph for errors before building.

    Verifies that all depends_on and parent references resolve, that there
    are no duplicate node IDs, and that no circular dependencies exist.
    Exits with code 1 if any errors are found.
    """
    config = _load_config(Path(".specdiff"))
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
            graph = build_graph(nodes)
            cascade(graph, list(node_map.keys()))
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

A spec FAILS if any of the following are true:
- An error response specifies an HTTP status code but not the response body field
  names (e.g., "return 422" fails; "return 422 with {error: 'password_too_weak'}" passes)
- Counting terms like "N rows" or "N items" are used without specifying whether the
  count includes headers, empty entries, or deleted records
- A validation rule combines conditions with "and" without listing every condition
  explicitly (e.g., "strong password" fails; ">= 12 chars, >= 1 uppercase, >= 1 digit,
  >= 1 special character" passes)
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
- If the spec describes state that persists across requests (a user store, a session
  store, a todo list, an event queue), include a dedicated module for it in the file
  plan. Request handlers must delegate to it -- never let mutable state live as a
  literal constant inside a handler function.
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
- For every function that can fail, include the exact error string in the docstring/JSDoc,
  not just the exception type. E.g.: 'Raises ValueError("duplicate column: {name}")'
  The testing agent uses these exact strings to write assertions.
- For store or repository modules, define the full CRUD surface: add, find-by-key,
  update, remove, and what happens on not-found (return None or raise KeyError, etc.).
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
- Never hardcode test or example data as production logic. An in-memory store
  means a real mutable collection (list, dict, Map) at module level -- never a
  literal like ['test@example.com'] or a check like 'if email == "admin@example.com"'.
- For TypeScript: import from real npm packages only (express, jsonwebtoken, bcrypt,
  uuid, etc.) -- never placeholder names like 'some-http-framework'.
- Every import you use must appear at the top of the file. Review each file before
  returning it; a missing import is a runtime error.
- If the spec lists multi-condition validation (e.g., password length + character
  classes), implement every condition -- never simplify to a single check.
""",
        "testing": """\
You are the Testing agent. The generated implementation code from the previous
stage is in your context (labelled generated_code). Read it before writing a
single test to find the exact module paths, function names, and return shapes.

Output ONLY a valid JSON object mapping each test file path to its complete
contents as a string. Return an empty object {} if no tests are appropriate.

Rules:
- Cover the happy path, all error cases, and edge cases stated in the spec.
- Import from the exact module paths present in the generated implementation.
- Use the test framework stated in the prompt; default to pytest (Python) or
  vitest (TypeScript) if none is specified.
- Test file naming: tests/test_<module>.py (Python) or <module>.test.ts (TS).
- Python: serialize test data with json.dumps(), never str(). Python's str() on
  a dict produces single-quoted output that json.loads() will reject.
- Python: pytest fixtures cannot accept inline call arguments. Use factory
  fixtures (return a callable) or plain helper functions instead.
- When asserting a JSON-encoded string, compute the expected value with
  json.dumps(expected, ...) using the same parameters as the implementation.
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
Additional failure conditions (always return passed: false if any of these apply):
- Any file imports from a placeholder package name (e.g., 'some-http-framework').
- Credentials, emails, or example data appear as hardcoded literals in production
  logic (e.g., checking email === 'test@example.com' instead of querying a store).
- A symbol is used in a file but its import is absent from that file.
- A multi-condition validation rule is only partially implemented.
""",
    }

    skills_dir = specs_dir / "skills"
    for name, content in skills.items():
        (skills_dir / f"{name}.skill.md").write_text(content)

    example_spec = """\
---
id: behaviors/hello
version: "1.0.0"
parent: behaviors
status: approved
depends_on: []
---

## Hello World

Replace this with your first real spec.

### Acceptance Criteria

- Given a name, the system returns "Hello, <name>!"
- If name is empty or not provided, defaults to "Hello, World!"
- Name is stripped of leading and trailing whitespace before use
"""
    behaviors_dir = specs_dir / "behaviors"
    behaviors_dir.mkdir()
    (behaviors_dir / "hello.spec.md").write_text(example_spec)

    click.echo("Initialized .specdiff/ with config, skill files, and an example spec.\n")
    click.echo("Next steps:")
    click.echo("  1. Set your API key:  export GEMINI_API_KEY=your-key-here")
    click.echo("  2. Edit .specdiff/behaviors/hello.spec.md with your first spec")
    click.echo("  3. Run `specdiff review behaviors/hello` to validate it")
    click.echo("  4. Run `specdiff build` to generate code")
    click.echo("  5. Run `specdiff ui` to explore your spec graph")


@cli.command()
@click.argument("node_id", required=False)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def clean(node_id: str | None, yes: bool) -> None:
    """Delete generated files and remove them from the hash map.

    Forces a full rebuild of NODE_ID (or all nodes) on the next build.
    """
    config = _load_config(Path(".specdiff"))
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
