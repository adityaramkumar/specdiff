from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from specdiff.agents.spec_agent import review_spec
from specdiff.types import SpecdiffConfig, SpecNode


def _make_node() -> SpecNode:
    return SpecNode(
        id="test/example",
        version="1.0.0",
        status="draft",
        hash="abc123",
        content="## Example\n\nHandle errors gracefully.",
        file_path=".specdiff/test/example.spec.md",
    )


def _mock_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.text = json.dumps(data)
    return resp


class TestReviewSpec:
    @patch("specdiff.agents.spec_agent.get_gemini_client")
    def test_pass(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = client
        client.models.generate_content.return_value = _mock_response(
            {
                "passed": True,
                "feedback": "- All criteria met.\n- Edge cases documented.",
                "proposed_revision": None,
            }
        )

        result = review_spec(_make_node(), "skill content", SpecdiffConfig())
        assert result.passed is True
        assert "criteria met" in result.feedback
        assert result.proposed_revision is None

    @patch("specdiff.agents.spec_agent.get_gemini_client")
    def test_fail_with_revision(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = client
        client.models.generate_content.return_value = _mock_response(
            {
                "passed": False,
                "feedback": "- 'handle errors gracefully' is vague.",
                "proposed_revision": "## Example\n\nReturn HTTP 500 on unhandled errors.",
            }
        )

        result = review_spec(_make_node(), "skill content", SpecdiffConfig())
        assert result.passed is False
        assert "vague" in result.feedback
        assert result.proposed_revision is not None
        assert "HTTP 500" in result.proposed_revision
