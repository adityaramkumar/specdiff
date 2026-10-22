from __future__ import annotations

from specdiff.providers import Completer, LLMResponse
from specdiff.providers.keys import require_env

# provider -> (API key env var, base URL; None means the OpenAI default)
ENDPOINTS = {
    "openai": ("OPENAI_API_KEY", None),
    "xai": ("XAI_API_KEY", "https://api.x.ai/v1"),
}


def make_completer(provider: str) -> Completer:
    key_env, base_url = ENDPOINTS[provider]

    def complete(model: str, prompt: str, system: str | None = None) -> LLMResponse:
        from openai import OpenAI

        client = OpenAI(api_key=require_env(key_env), base_url=base_url)
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=model, messages=messages)
        usage = response.usage
        return LLMResponse(
            text=response.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    return complete
