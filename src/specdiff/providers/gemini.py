from __future__ import annotations

from google import genai

from specdiff.providers import LLMResponse
from specdiff.providers.keys import require_env


def complete(model: str, prompt: str, system: str | None = None) -> LLMResponse:
    client = genai.Client(api_key=require_env("GEMINI_API_KEY"))
    config = {"system_instruction": system} if system else None
    response = client.models.generate_content(model=model, contents=prompt, config=config)
    usage = response.usage_metadata
    return LLMResponse(
        text=response.text or "",
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
    )
