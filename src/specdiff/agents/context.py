from __future__ import annotations

from dataclasses import dataclass, field

from specdiff.agents import fileblocks
from specdiff.types import SpecNode

LANGUAGE_NOTES = {
    "python": (
        "The output directory is the import root when tests run. Import project modules "
        "by absolute name from it (`from auth.login import login`); never use relative "
        "imports. Name test files test_*.py."
    ),
    "typescript": (
        "Use ES module syntax and relative imports between project files. Import test "
        "helpers explicitly from the test framework (e.g. `import { describe, it, expect } "
        "from 'vitest'`)."
    ),
}


@dataclass
class NodeContext:
    """Everything an agent needs to know about one spec node and the project around it.

    All file paths are relative to output_dir.
    """

    node: SpecNode
    language: str
    output_dir: str
    ancestors: list[SpecNode] = field(default_factory=list)
    deps: list[SpecNode] = field(default_factory=list)
    dep_files: dict[str, str] = field(default_factory=dict)
    own_files: dict[str, str] = field(default_factory=dict)
    others: dict[str, str] = field(default_factory=dict)
    test_framework: str | None = None
    test_command: str | None = None
    check_command: str | None = None


def render(ctx: NodeContext) -> str:
    """The shared prompt prefix every stage sees, most stable sections first."""
    node = ctx.node
    sections = [_project_section(ctx)]

    for parent in ctx.ancestors:
        sections.append(
            f"# Parent spec `{parent.id}` (constraints this spec inherits)\n\n"
            f"{parent.content.strip()}"
        )
    for dep in ctx.deps:
        sections.append(f"# Dependency spec `{dep.id}`\n\n{dep.content.strip()}")
    if ctx.dep_files:
        sections.append(
            "# Dependency code\n\nAlready built from the dependency specs. Import from "
            "these files; do not rewrite or duplicate them.\n\n" + fileblocks.render(ctx.dep_files)
        )
    if ctx.others:
        listing = "\n".join(f"- {path} (owned by `{owner}`)" for path, owner in ctx.others.items())
        sections.append(
            "# Files owned by other specs\n\nNever write to these paths, and do not create "
            f"modules that duplicate them.\n\n{listing}"
        )
    if ctx.own_files:
        sections.append(
            "# This spec's current files (from its last build)\n\nChange only what the spec "
            "now requires; keep everything else as it is.\n\n" + fileblocks.render(ctx.own_files)
        )
    sections.append(
        f"# Spec `{node.id}` (version {node.version}) -- the one you are building\n\n"
        f"{node.content.strip()}"
    )
    return "\n\n".join(sections) + "\n"


def _project_section(ctx: NodeContext) -> str:
    lines = [
        "# Project",
        "",
        f"- Language: {ctx.language}",
        f"- Output directory: {ctx.output_dir}/ (every path you write is relative to it)",
    ]
    if ctx.test_framework:
        lines.append(f"- Test framework: {ctx.test_framework}")
    if ctx.test_command:
        lines.append(f"- Tests run from the project root with: `{ctx.test_command}`")
    if ctx.check_command:
        lines.append(f"- Code must also pass: `{ctx.check_command}`")
    if note := LANGUAGE_NOTES.get(ctx.language):
        lines.append(f"- {note}")
    return "\n".join(lines)
