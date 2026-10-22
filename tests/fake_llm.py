"""A scripted stand-in for every LLM provider, used at the providers boundary."""

from __future__ import annotations

import re
from collections import defaultdict

from specdiff.providers import LLMResponse

_NODE = re.compile(r"# Spec `([^`]+)` \(version")
_STAGE = re.compile(r"# Your task: (\w+)")


def slug(node_id: str) -> str:
    return node_id.replace("/", "_").replace("-", "_")


def default_reply(node_id: str, stage: str) -> str:
    """A well-behaved model: one module and one passing test per node."""
    s = slug(node_id)
    if stage == "plan":
        return (
            f'<code path="{s}.py">implements {node_id}</code>\n'
            f'<test path="test_{s}.py">tests {node_id}</test>\n'
            f"<interface>\nVALUE: str\n</interface>"
        )
    if stage == "implement":
        return f'<file path="{s}.py">\nVALUE = "{node_id}"\n</file>'
    if stage == "test":
        return (
            f'<file path="test_{s}.py">\nfrom {s} import VALUE\n\n\n'
            f'def test_value():\n    assert VALUE == "{node_id}"\n</file>'
        )
    if stage == "review":
        return "<verdict>pass</verdict>\n<feedback>ok</feedback>"
    if stage == "repair":
        return ""
    raise AssertionError(f"unexpected stage {stage}")


class FakeLLM:
    """Replies by (node, stage). Scripted replies are used first, in order."""

    def __init__(self) -> None:
        self.script: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.calls: list[tuple[str, str]] = []
        self.prompts: list[str] = []

    def reply(self, node_id: str, stage: str, *texts: str) -> FakeLLM:
        self.script[(node_id, stage)].extend(texts)
        return self

    def stages(self, node_id: str) -> list[str]:
        return [stage for node, stage in self.calls if node == node_id]

    def __call__(self, model: str, prompt: str, system: str | None = None) -> LLMResponse:
        node = _NODE.search(prompt).group(1)
        stage = _STAGE.search(prompt).group(1)
        self.calls.append((node, stage))
        self.prompts.append(prompt)
        queued = self.script[(node, stage)]
        text = queued.pop(0) if queued else default_reply(node, stage)
        return LLMResponse(text=text, input_tokens=100, output_tokens=10)
