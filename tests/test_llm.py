from __future__ import annotations

import json
import os

import click
import pytest

from specdiff.llm import extract_json
from specdiff.providers import detect_provider
from specdiff.providers.keys import require_env


class TestExtractJson:
    def test_bare_json_object(self):
        assert extract_json('{"key": "value"}') == {"key": "value"}

    def test_bare_json_array(self):
        assert extract_json("[1, 2, 3]") == [1, 2, 3]

    def test_fenced_json(self):
        text = '```\n{"key": "value"}\n```'
        assert extract_json(text) == {"key": "value"}

    def test_fenced_json_with_language_tag(self):
        text = '```json\n{"key": "value"}\n```'
        assert extract_json(text) == {"key": "value"}

    def test_prose_wrapped_json(self):
        text = 'Here is the result:\n{"key": "value"}'
        assert extract_json(text) == {"key": "value"}

    def test_nested_json(self):
        data = {"outer": {"inner": "value"}, "list": [1, 2, 3]}
        assert extract_json(json.dumps(data)) == data

    def test_whitespace_stripped(self):
        assert extract_json('  {"a": 1}  ') == {"a": 1}

    def test_invalid_json_raises(self):
        import json as _json

        with pytest.raises(_json.JSONDecodeError):
            extract_json("not json at all")

    def test_fenced_empty_object(self):
        assert extract_json("```json\n{}\n```") == {}

    def test_multiline_fenced_json(self):
        text = '```json\n{\n  "a": 1,\n  "b": 2\n}\n```'
        assert extract_json(text) == {"a": 1, "b": 2}


class TestDetectProvider:
    @pytest.mark.parametrize(
        ("model", "provider"),
        [
            ("gemini-2.5-flash", "gemini"),
            ("claude-opus-5-5", "anthropic"),
            ("grok-4-fast", "xai"),
            ("gpt-5", "openai"),
            ("o3-mini", "openai"),
        ],
    )
    def test_prefixes(self, model, provider):
        assert detect_provider(model) == provider

    def test_unknown_model_is_an_error_not_a_silent_fallback(self):
        with pytest.raises(click.ClickException, match="Supported model name prefixes"):
            detect_provider("llama-3")


class TestRequireEnv:
    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("TEST_SPECDIFF_KEY_ABC", "my-secret-key")
        assert require_env("TEST_SPECDIFF_KEY_ABC") == "my-secret-key"

    def test_missing_key_explains_how_to_set_it(self):
        os.environ.pop("MISSING_SPECDIFF_KEY_XYZ", None)
        with pytest.raises(click.ClickException) as exc_info:
            require_env("MISSING_SPECDIFF_KEY_XYZ")
        message = exc_info.value.format_message()
        assert "MISSING_SPECDIFF_KEY_XYZ" in message and "export" in message
