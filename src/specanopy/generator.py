from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import click
from google import genai

from specanopy.types import SpecNode, SpecanopyConfig

TRACEABILITY_TEMPLATE = (
    "# generated_from: {node_id}\n"
    "# spec_hash: {spec_hash}\n"
    "# generated_at: {timestamp}\n"
    "# agent: implementation-agent-v0.1\n"
)

SYSTEM_PROMPT = (
    "You are a code generator. You receive a spec and produce source files.\n"
    "Reply with ONLY a JSON object where each key is a file path relative to "
    "the output directory (do NOT include the output directory itself in the key) "
    "and each value is the full file contents as a string. No explanation, no "
    "markdown fences, just the raw JSON object."
)


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise click.ClickException(
            "GEMINI_API_KEY not set. Export it:\n\n"
            "  export GEMINI_API_KEY=your-key-here\n"
        )
    return key


def _extract_json(text: str) -> dict[str, str]:
    """Extract a JSON object from the response, stripping code fences if present."""
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1).strip()
    return json.loads(stripped)


def _traceability_header(node: SpecNode) -> str:
    return TRACEABILITY_TEMPLATE.format(
        node_id=node.id,
        spec_hash=node.hash,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def generate(node: SpecNode, config: SpecanopyConfig) -> list[str]:
    """Generate code files from a spec node via the Gemini API.

    Returns the list of written file paths (relative to project root).
    """
    api_key = _get_api_key()
    client = genai.Client(api_key=api_key)

    prompt = (
        f"Spec ID: {node.id}\n"
        f"Version: {node.version}\n\n"
        f"--- SPEC CONTENT ---\n{node.content}\n--- END SPEC ---\n\n"
        f"Generate the implementation files. Output directory: {config.output_dir}"
    )

    response = client.models.generate_content(
        model=config.model,
        config={"system_instruction": SYSTEM_PROMPT},
        contents=prompt,
    )

    files = _extract_json(response.text)
    header = _traceability_header(node)
    written: list[str] = []

    for rel_path, contents in files.items():
        full_path = Path(config.output_dir) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(header + "\n" + contents, "utf-8")
        written.append(str(full_path))

    return written
