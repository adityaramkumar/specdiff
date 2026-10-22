from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import click


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


Completer = Callable[[str, str, str | None], LLMResponse]

# Model-name prefix -> provider module name. Checked in order.
PREFIXES: list[tuple[str, str]] = [
    ("gemini", "gemini"),
    ("claude", "anthropic"),
    ("grok", "xai"),
    ("gpt", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
]


def detect_provider(model: str) -> str:
    """Name the provider that serves this model, by model-name prefix."""
    for prefix, provider in PREFIXES:
        if model.startswith(prefix):
            return provider
    known = ", ".join(sorted({p for p, _ in PREFIXES}))
    raise click.ClickException(
        f"Don't know which provider serves model '{model}'. Supported model name prefixes: {known}."
    )


def complete(model: str, prompt: str, system: str | None = None) -> LLMResponse:
    """Send one prompt to the model's provider and return its text and token usage."""
    provider = detect_provider(model)
    if provider == "gemini":
        from specdiff.providers.gemini import complete as impl
    elif provider == "anthropic":
        from specdiff.providers.claude import complete as impl
    else:
        from specdiff.providers.openai_compat import make_completer

        impl = make_completer(provider)
    return impl(model, prompt, system)
