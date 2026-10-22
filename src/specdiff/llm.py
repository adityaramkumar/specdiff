from __future__ import annotations

import json
import re

from specdiff.providers import LLMResponse, complete


def generate_content(
    model: str, contents: str, system_instruction: str | None = None
) -> LLMResponse:
    """Generate text from any supported LLM provider."""
    return complete(model, contents, system_instruction)


def extract_json(text: str) -> dict | list:
    """Extract a JSON object/array from LLM output, stripping fences and prose."""
    stripped = text.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1).strip()

    # If the model added prose before the JSON, seek the first { or [ and use
    # raw_decode so we stop at the end of the first complete JSON value rather
    # than greedily matching to the last } or ] in the string.
    if stripped and stripped[0] not in ("{", "["):
        start = min(
            (stripped.find(c) for c in ("{", "[") if stripped.find(c) != -1),
            default=-1,
        )
        if start != -1:
            stripped = stripped[start:]

    value, _ = json.JSONDecoder().raw_decode(stripped)
    return value
