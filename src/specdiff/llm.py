from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import click
from google import genai


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ProviderConfig:
    api_key_env: str
    base_url: str | None = None


PROVIDERS: dict[str, ProviderConfig] = {
    "gemini": ProviderConfig(api_key_env="GEMINI_API_KEY"),
    "grok": ProviderConfig(api_key_env="XAI_API_KEY", base_url="https://api.x.ai/v1"),
    # "gpt": ProviderConfig(api_key_env="OPENAI_API_KEY", base_url="https://api.openai.com/v1"),
}


def detect_provider(model: str) -> tuple[str, ProviderConfig]:
    """Match a model name to its provider by prefix."""
    for prefix, config in PROVIDERS.items():
        if model.startswith(prefix):
            return prefix, config
    return "gemini", PROVIDERS["gemini"]


def _get_api_key(config: ProviderConfig) -> str:
    key = os.environ.get(config.api_key_env)
    if not key:
        raise click.ClickException(
            f"{config.api_key_env} not set. Export it:\n\n"
            f"  export {config.api_key_env}=your-key-here\n"
        )
    return key


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using the GEMINI_API_KEY env var."""
    return genai.Client(api_key=_get_api_key(PROVIDERS["gemini"]))


def _generate_gemini(
    model: str, contents: str, system_instruction: str | None = None
) -> LLMResponse:
    client = get_gemini_client()
    config = {}
    if system_instruction:
        config["system_instruction"] = system_instruction
    response = client.models.generate_content(model=model, contents=contents, config=config or None)
    return LLMResponse(
        text=response.text,
        input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0),
        output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0),
    )


def _generate_openai_compat(
    model: str,
    provider: ProviderConfig,
    contents: str,
    system_instruction: str | None = None,
) -> LLMResponse:
    from openai import OpenAI

    client = OpenAI(api_key=_get_api_key(provider), base_url=provider.base_url)
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": contents})
    response = client.chat.completions.create(model=model, messages=messages)
    choice = response.choices[0]
    usage = response.usage
    return LLMResponse(
        text=choice.message.content or "",
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


def generate_content(
    model: str, contents: str, system_instruction: str | None = None
) -> LLMResponse:
    """Generate text from any supported LLM provider."""
    provider_name, provider_config = detect_provider(model)
    if provider_name == "gemini":
        return _generate_gemini(model, contents, system_instruction)
    return _generate_openai_compat(model, provider_config, contents, system_instruction)


def extract_json(text: str) -> dict | list:
    """Extract a JSON object/array from LLM output, stripping fences and prose."""
    stripped = text.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1).strip()

    # If the model added prose around the JSON, find the outermost { } or [ ]
    if stripped and stripped[0] not in ("{", "["):
        obj = re.search(r"(\{.*\}|\[.*\])", stripped, re.DOTALL)
        if obj:
            stripped = obj.group(1).strip()

    return json.loads(stripped)
