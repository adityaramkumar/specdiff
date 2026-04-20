from __future__ import annotations

from specdiff.llm import extract_json
from specdiff.types import FilePlan, SpecNode


def format_architect_prompt(node: SpecNode, dep_specs: list[SpecNode] | None = None) -> str:
    """Build the prompt that the Architect Agent receives."""
    dep_context = ""
    for dep in dep_specs or []:
        suffix = "..." if len(dep.content) > 200 else ""
        dep_context += f"\n- {dep.id}: {dep.content[:200]}{suffix}"

    return (
        f"Spec: {node.id} v{node.version}\n\n"
        f"{node.content}\n\n"
        f"Dependencies:{dep_context or ' none'}\n\n"
        "Produce a file plan as a JSON object where keys are relative file paths "
        "and values describe each file's purpose."
    )


def parse_file_plan(raw_output: str) -> FilePlan:
    """Parse the Architect Agent's JSON output into a FilePlan."""
    try:
        data = extract_json(raw_output)
    except Exception:
        data = {}
    return FilePlan(files=data)
