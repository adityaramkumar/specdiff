"""Each eval case must be solvable: its reference solution, fed through the real
pipeline in place of a model, has to build and pass every hidden test."""

from __future__ import annotations

import pytest
import yaml

from evals.run import CASES, run_case
from tests.fake_llm import FakeLLM

CASE_DIRS = sorted(p for p in CASES.iterdir() if (p / "specs").is_dir())


def _reference_llm(case) -> FakeLLM:
    llm = FakeLLM()
    mapping = yaml.safe_load((case / "case.yaml").read_text())["reference"]
    for spec_id, files in mapping.items():
        plan = "".join(f'<code path="{f}">reference</code>' for f in files)
        llm.reply(spec_id, "plan", plan + "<interface>\n</interface>")
        blocks = "".join(
            f'<file path="{f}">\n{(case / "reference" / f).read_text()}</file>\n' for f in files
        )
        llm.reply(spec_id, "implement", blocks)
    return llm


@pytest.mark.parametrize("case", CASE_DIRS, ids=lambda p: p.name)
def test_reference_solution_passes_hidden_tests(case, monkeypatch):
    monkeypatch.setattr("specdiff.agents.stages.complete", _reference_llm(case))

    result = run_case(case, model="reference")

    assert result.built == result.specs
    assert result.hidden_total > 0
    assert result.hidden_passed == result.hidden_total
