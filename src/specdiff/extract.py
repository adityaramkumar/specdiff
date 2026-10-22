"""Draft specs from an existing codebase.

Everything extract writes is a draft: a model's reading of code needs a human
review before it drives generation.
"""

from __future__ import annotations

import os
from pathlib import Path

import click
import frontmatter

from specdiff.agents import fileblocks
from specdiff.build.files import resolve_output_path
from specdiff.llm import generate_content
from specdiff.types import SpecdiffConfig

CONSTITUTION_ID = "constitution"
_EXTENSIONS = (".py", ".js", ".ts", ".go", ".java", ".json", ".yaml", ".md")
_IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".specdiff", "ui",
                "ui_dist", "dist", "build"}  # fmt: skip

_SPEC_FORMAT = """
Return each spec as a block whose path ends in .spec.md:

<file path="{folder}/<name>.spec.md">
---
id: {folder}/<name>
version: "1.0.0"
status: draft{extra_frontmatter}
---

The spec body in Markdown: behavior, inputs and outputs, exact error messages.
</file>
"""


def generate_specs_from_code(
    src_dir: Path, specs_dir: Path, config: SpecdiffConfig, granularity: str = "auto"
) -> None:
    """Read a codebase and write draft spec files for it."""
    click.echo(f"Analyzing codebase in {src_dir}...")
    code = {f["path"]: f["content"] for f in _collect_source_files(src_dir)}
    if not code:
        click.echo(f"No valid source files found in {src_dir}.")
        return
    code_text = fileblocks.render(code)

    has_constitution = _write_constitution(config.model, code_text, specs_dir)
    parent = CONSTITUTION_ID if has_constitution else None
    if granularity == "file":
        written = _extract_file_by_file(config.model, code, specs_dir, parent)
    else:
        written = _extract_auto(config.model, code_text, specs_dir, parent)

    click.echo(
        f"\nWrote {len(written)} draft spec(s). Review each one, then set `status: approved` "
        "on the ones that capture your intent."
    )


def _collect_source_files(src_dir: Path) -> list[dict[str, str]]:
    code_files: list[dict[str, str]] = []
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for file in files:
            if file.endswith(_EXTENSIONS):
                path = Path(root) / file
                try:
                    content = path.read_text("utf-8")
                except UnicodeDecodeError:
                    continue
                code_files.append({"path": str(path.relative_to(src_dir)), "content": content})
    return code_files


def _write_constitution(model: str, code_text: str, specs_dir: Path) -> bool:
    """Summarise project-wide conventions as a context-only spec the others inherit."""
    path = specs_dir / f"{CONSTITUTION_ID}.spec.md"
    if path.exists():
        click.echo(f"  Kept existing {path.name}")
        return True
    click.echo("Summarising architecture and conventions...")
    prompt = (
        "Describe this codebase's architecture and conventions for agents that will "
        "regenerate parts of it: module layout, naming, error handling, data formats, "
        "external services, and patterns every module follows. Write plain Markdown, "
        "no fences.\n\n" + code_text
    )
    try:
        body = generate_content(model=model, contents=prompt).text.strip()
    except Exception as exc:
        click.echo(f"  Warning: could not summarise architecture: {exc}", err=True)
        return False
    post = frontmatter.Post(
        body, id=CONSTITUTION_ID, version="1.0.0", status="draft", generate=False
    )
    specs_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dumps(post) + "\n", "utf-8")
    click.echo(f"  Created {path.name}")
    return True


def _extract_auto(model: str, code_text: str, specs_dir: Path, parent: str | None) -> list[str]:
    click.echo("Extracting contracts...")
    prompt = (
        "Extract this codebase's data models, schemas and API definitions as contract "
        "specs, one per coherent contract.\n" + _SPEC_FORMAT.format(folder="contracts",
        extra_frontmatter="") + "\nCodebase:\n" + code_text
    )  # fmt: skip
    contracts = _write_specs(generate_content(model=model, contents=prompt).text, specs_dir, parent)

    click.echo("Extracting behaviors...")
    listing = "\n".join(f"- {c}" for c in contracts) or "- (none)"
    prompt = (
        "Extract this codebase's features and workflows as behavior specs. Link each "
        "to the contracts it uses with depends_on.\n\nContracts:\n" + listing + "\n"
        + _SPEC_FORMAT.format(folder="behaviors", extra_frontmatter="\ndepends_on:\n"
        "  - contracts/<contract it uses>") + "\nCodebase:\n" + code_text
    )  # fmt: skip
    behaviors = _write_specs(generate_content(model=model, contents=prompt).text, specs_dir, parent)
    return contracts + behaviors


def _extract_file_by_file(
    model: str, code: dict[str, str], specs_dir: Path, parent: str | None
) -> list[str]:
    click.echo(f"Extracting one spec per file for {len(code)} files...")
    listing = "\n".join(f"- {p}" for p in code)
    written: list[str] = []
    for path, content in code.items():
        click.echo(f"  Processing {path}...")
        prompt = (
            f"Write one behavior spec for the source file {path}.\n"
            + _SPEC_FORMAT.format(folder="behaviors", extra_frontmatter="")
            + f"\nOther files in the project:\n{listing}\n\n"
            + fileblocks.render({path: content})
        )
        try:
            written += _write_specs(generate_content(model=model, contents=prompt).text,
                                    specs_dir, parent)  # fmt: skip
        except Exception as exc:
            click.echo(f"    Failed to process {path}: {exc}", err=True)
    return written


def _write_specs(reply: str, specs_dir: Path, parent: str | None) -> list[str]:
    """Write each spec block as a draft. Returns the IDs written; never overwrites."""
    written: list[str] = []
    for rel, content in fileblocks.parse(reply).files.items():
        if not rel.endswith(".spec.md"):
            rel += ".spec.md"
        try:
            path = resolve_output_path(str(specs_dir), rel)
        except ValueError as exc:
            click.echo(f"  Skipped {rel}: {exc}", err=True)
            continue
        post = frontmatter.loads(content)
        spec_id = post.metadata.get("id")
        if not spec_id:
            click.echo(f"  Skipped {rel}: no id in frontmatter", err=True)
            continue
        if path.exists():
            click.echo(f"  Kept existing {rel}")
            continue
        post.metadata["status"] = "draft"
        if parent and spec_id != parent:
            post.metadata.setdefault("parent", parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.dumps(post) + "\n", "utf-8")
        written.append(spec_id)
        click.echo(f"  Created {rel}")
    return written
