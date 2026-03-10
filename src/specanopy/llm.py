from __future__ import annotations

import json
import os
import re

import click
from google import genai


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using the GEMINI_API_KEY env var."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise click.ClickException(
            "GEMINI_API_KEY not set. Export it:\n\n  export GEMINI_API_KEY=your-key-here\n"
        )
    return genai.Client(api_key=key)


def extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output, stripping code fences if present."""
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1).strip()
    return json.loads(stripped)
