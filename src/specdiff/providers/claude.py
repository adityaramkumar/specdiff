from __future__ import annotations

import click

from specdiff.providers import LLMResponse
from specdiff.providers.keys import require_env

# Generated files can be long, so stream with a generous output cap.
MAX_TOKENS = 64000
# Models that accept the server-side refusal fallback; others are called without it.
FALLBACK_MODELS = ("claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def complete(model: str, prompt: str, system: str | None = None) -> LLMResponse:
    import anthropic

    client = anthropic.Anthropic(api_key=require_env("ANTHROPIC_API_KEY"))
    kwargs: dict = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    if model in FALLBACK_MODELS:
        stream = client.beta.messages.stream(**kwargs, betas=[FALLBACK_BETA], fallbacks="default")
    else:
        stream = client.messages.stream(**kwargs)
    with stream as s:
        message = s.get_final_message()

    if message.stop_reason == "refusal":
        category = getattr(message.stop_details, "category", None)
        raise click.ClickException(f"{model} declined the request (category: {category}).")
    if message.stop_reason == "max_tokens":
        raise click.ClickException(f"{model} hit the {MAX_TOKENS}-token output limit.")

    return LLMResponse(
        text="".join(b.text for b in message.content if b.type == "text"),
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )
