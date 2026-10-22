from __future__ import annotations

import sys
from pathlib import Path

import click
import frontmatter

from specdiff.agents.spec_agent import review_spec
from specdiff.cli.common import SPEC_EVAL_SKILL, project_config
from specdiff.parser import discover_specs
from specdiff.skills import load_skill


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


@click.command()
@click.argument("node_id", required=False)
def review(node_id: str | None) -> None:
    """Review specs for quality. Optionally target a single NODE_ID."""
    config, specs_dir = project_config()

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
