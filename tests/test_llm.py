from __future__ import annotations

import json
import os
from unittest.mock import patch

import click
import pytest

from specdiff.llm import (
    ProviderConfig,
    _get_api_key,
    detect_provider,
    extract_json,
)


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
    def test_gemini_prefix(self):
        name, config = detect_provider("gemini-2.5-flash")
        assert name == "gemini"
        assert config.api_key_env == "GEMINI_API_KEY"

    def test_grok_prefix(self):
        name, config = detect_provider("grok-4-fast")
        assert name == "grok"
        assert config.api_key_env == "XAI_API_KEY"
        assert config.base_url is not None

    def test_unknown_falls_back_to_gemini(self):
        name, config = detect_provider("unknown-model-xyz")
        assert name == "gemini"
        assert config.api_key_env == "GEMINI_API_KEY"

    def test_gemini_lite_variant(self):
        name, _ = detect_provider("gemini-2.0-flash-lite")
        assert name == "gemini"

    def test_grok_returns_xai_base_url(self):
        _, config = detect_provider("grok-anything")
        assert "x.ai" in (config.base_url or "")


class TestGetApiKey:
    def test_returns_key_when_set(self):
        config = ProviderConfig(api_key_env="TEST_SPECDIFF_KEY_ABC")
        with patch.dict("os.environ", {"TEST_SPECDIFF_KEY_ABC": "my-secret-key"}):
            assert _get_api_key(config) == "my-secret-key"

    def test_raises_click_exception_when_missing(self):
        config = ProviderConfig(api_key_env="MISSING_SPECDIFF_KEY_XYZ")
        os.environ.pop("MISSING_SPECDIFF_KEY_XYZ", None)
        with pytest.raises(click.ClickException) as exc_info:
            _get_api_key(config)
        assert "MISSING_SPECDIFF_KEY_XYZ" in str(exc_info.value.format_message())

    def test_error_message_includes_export_hint(self):
        config = ProviderConfig(api_key_env="MY_TEST_KEY_FOR_HINT")
        os.environ.pop("MY_TEST_KEY_FOR_HINT", None)
        with pytest.raises(click.ClickException) as exc_info:
            _get_api_key(config)
        assert "export" in exc_info.value.format_message().lower()
