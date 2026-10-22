from __future__ import annotations

import pytest

from tests.fake_llm import FakeLLM


@pytest.fixture
def fake_llm(monkeypatch) -> FakeLLM:
    llm = FakeLLM()
    monkeypatch.setattr("specdiff.agents.stages.complete", llm)
    return llm
