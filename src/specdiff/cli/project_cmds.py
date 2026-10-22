from __future__ import annotations

import sys
from pathlib import Path

import click

from specdiff import hashmap
from specdiff.cli.common import project_config
from specdiff.cli.templates import EXAMPLE_SPEC, INIT_CONFIG, SKILLS_README
from specdiff.skills import load_skill


@click.command()
@click.option("--port", default=8000, help="Port to run the UI server on")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically")
def ui(port: int, no_browser: bool) -> None:
    """Launch the interactive graphical UI in your browser."""
    config, specs_dir = project_config()

    # We delay this import to avoid circular dependency if `api` imports from `cli`
    from specdiff.api import serve_ui

    serve_ui(specs_dir, port=port, open_browser=not no_browser)


@click.command()
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


@click.command()
@click.argument("name")
def skill(name: str) -> None:
    """Print the skill NAME as the build uses it (your override or the built-in)."""
    try:
        click.echo(load_skill(project_config()[1], name), nl=False)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


@click.command()
@click.argument("node_id", required=False)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def clean(node_id: str | None, yes: bool) -> None:
    """Delete generated files and remove them from the hash map.

    Forces a full rebuild of NODE_ID (or all nodes) on the next build.
    """
    config, specs_dir = project_config()
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


@click.command()
@click.option("--source", default=".", help="Directory to read code from")
@click.option("--granularity", default="auto", help="Extraction granularity ('auto' or 'file')")
def extract(source: str, granularity: str) -> None:
    """Read existing code and generate spec files."""
    config, specs_dir = project_config()

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
