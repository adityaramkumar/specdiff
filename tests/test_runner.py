from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from specdiff import hashmap
from specdiff.build.files import BACKUP_DIR
from specdiff.build.runner import BuildRefused, execute_build
from specdiff.graph import build_graph
from specdiff.types import HashMap, SpecdiffConfig, SpecNode

TEST_COMMAND = f"PYTHONPATH=src {sys.executable} -m pytest -q -p no:cacheprovider src"


def _node(node_id: str, depends_on: list[str] | None = None, h: str | None = None) -> SpecNode:
    return SpecNode(
        id=node_id,
        version="1.0.0",
        status="approved",
        hash=h or f"hash-{node_id}",
        content=f"Spec body for {node_id}.",
        file_path=f".specdiff/{node_id}.spec.md",
        depends_on=depends_on or [],
    )


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    specs_dir = tmp_path / ".specdiff"
    specs_dir.mkdir()
    return specs_dir


def _build(specs_dir, nodes, hm=None, *, review=True, force=False, **config):
    config.setdefault("test_command", TEST_COMMAND)
    hm = hm if hm is not None else HashMap()
    graph = build_graph(nodes)
    report = execute_build(
        nodes, SpecdiffConfig(**config), hm, graph, specs_dir, review=review, force=force
    )
    return report, hm


class TestSuccessfulBuild:
    def test_writes_files_runs_tests_and_saves_progress(self, project, fake_llm):
        report, hm = _build(project, [_node("auth/login")])

        assert report.ok and report.built == ["auth/login"]
        assert fake_llm.stages("auth/login") == ["plan", "implement", "test", "review"]
        code = Path("src/auth_login.py").read_text()
        assert code.startswith("# generated_from: auth/login")
        assert set(hm.nodes["auth/login"].generated_files) == {
            "src/auth_login.py",
            "src/test_auth_login.py",
        }
        saved = json.loads((project / "hash-map.json").read_text())
        assert "auth/login" in saved
        assert report.usage.calls == 4
        assert not (project / BACKUP_DIR).exists()

    def test_dependency_code_reaches_the_dependent_prompt(self, project, fake_llm):
        nodes = [_node("contracts/users"), _node("auth/login", depends_on=["contracts/users"])]
        _build(project, nodes)

        login_plan = next(
            p
            for (n, s), p in zip(fake_llm.calls, fake_llm.prompts, strict=True)
            if n == "auth/login" and s == "plan"
        )
        assert '<file path="contracts_users.py">\nVALUE = "contracts/users"' in login_plan
        assert "generated_from" not in login_plan

    def test_without_test_command_no_tests_are_written(self, project, fake_llm):
        report, _ = _build(project, [_node("a")], test_command=None)
        assert report.ok
        assert fake_llm.stages("a") == ["plan", "implement", "review"]

    def test_no_review_skips_review(self, project, fake_llm):
        _build(project, [_node("a")], review=False)
        assert "review" not in fake_llm.stages("a")


class TestRepairLoop:
    def test_failing_test_output_is_fed_to_repair(self, project, fake_llm):
        fake_llm.reply("a", "implement", '<file path="a.py">\nVALUE = "wrong"\n</file>')
        fake_llm.reply("a", "repair", '<file path="a.py">\nVALUE = "a"\n</file>')

        report, _ = _build(project, [_node("a")])

        assert report.ok
        assert fake_llm.stages("a") == ["plan", "implement", "test", "repair", "review"]
        repair_prompt = fake_llm.prompts[fake_llm.calls.index(("a", "repair"))]
        assert "Tests failed" in repair_prompt
        assert "AssertionError" in repair_prompt
        assert Path("src/a.py").read_text().endswith('VALUE = "a"\n')

    def test_syntax_error_is_caught_before_running_anything(self, project, fake_llm):
        fake_llm.reply("a", "implement", '<file path="a.py">\nVALUE = "a\n</file>')
        fake_llm.reply("a", "repair", '<file path="a.py">\nVALUE = "a"\n</file>')

        with patch("specdiff.agents.pipeline.run_command", wraps=None) as run:
            run.return_value = (True, "")
            report, _ = _build(project, [_node("a")])

        assert report.ok
        repair_prompt = fake_llm.prompts[fake_llm.calls.index(("a", "repair"))]
        assert "a.py:1: SyntaxError" in repair_prompt
        assert run.call_count == 1

    def test_review_failure_goes_to_repair(self, project, fake_llm):
        fake_llm.reply("a", "review", "<verdict>fail</verdict><feedback>missing X</feedback>")
        fake_llm.reply("a", "repair", '<file path="a.py">\nVALUE = "a"\nX = 1\n</file>')

        report, _ = _build(project, [_node("a")])

        assert report.ok
        assert fake_llm.stages("a")[-3:] == ["review", "repair", "review"]
        assert "missing X" in fake_llm.prompts[fake_llm.calls.index(("a", "repair"))]


class TestFailureIsolation:
    def test_failed_node_rolls_back_and_blocks_only_its_dependents(self, project, fake_llm):
        fake_llm.reply("a", "implement", '<file path="a.py">\nVALUE = "wrong"\n</file>')
        nodes = [_node("a"), _node("b", depends_on=["a"]), _node("c")]

        report, hm = _build(project, nodes, max_retries=1)

        assert report.failed.keys() == {"a"}
        assert "Tests failed" in report.failed["a"]
        assert report.skipped == {"b": "waits on a"}
        assert report.built == ["c"]
        assert not Path("src/a.py").exists()
        assert set(hm.nodes) == {"c"}
        assert fake_llm.stages("b") == []

    def test_writing_another_specs_file_is_rejected(self, project, fake_llm):
        _build(project, [_node("a")])
        fake_llm.reply("b", "implement", '<file path="a.py">\nVALUE = "b"\n</file>')
        fake_llm.reply(
            "b", "repair", '<delete path="a.py"/>\n<file path="b.py">\nVALUE = "b"\n</file>'
        )

        report, _ = _build(project, [_node("b")], hashmap.load(project))

        assert report.ok
        assert "a.py belongs to spec `a`" in fake_llm.prompts[fake_llm.calls.index(("b", "repair"))]
        assert Path("src/a.py").read_text().endswith('VALUE = "a"\n')

    def test_escaping_path_never_reaches_disk(self, project, fake_llm):
        fake_llm.reply("a", "implement", '<file path="../evil.py">\nx = 1\n</file>')
        report, _ = _build(project, [_node("a")], max_retries=0)

        assert "escapes output_dir" in report.failed["a"]
        assert not Path("evil.py").exists()


class TestIncrementalRebuild:
    def test_unchanged_files_are_kept_and_dropped_files_deleted(self, project, fake_llm):
        _, hm = _build(project, [_node("a")])
        fake_llm.reply(
            "a",
            "plan",
            '<code path="a.py">x</code><code path="extra.py">y</code>'
            '<test path="test_a.py">t</test><interface>\n</interface>',
        )
        fake_llm.reply(
            "a", "implement", '<unchanged path="a.py"/>\n<file path="extra.py">\nY = 2\n</file>'
        )
        fake_llm.reply("a", "test", '<file path="test_a.py">\ndef test_ok():\n    pass\n</file>')

        report, hm = _build(project, [_node("a", h="v2")], hm)

        assert report.ok
        plan_prompt = fake_llm.prompts[fake_llm.calls.index(("a", "plan"), 1)]
        assert "This spec's current files" in plan_prompt
        assert Path("src/a.py").read_text().count("generated_from") == 1
        assert Path("src/extra.py").exists()
        assert set(hm.nodes["a"].generated_files) == {"src/a.py", "src/extra.py", "src/test_a.py"}


class TestPreflight:
    def test_leftover_backup_refuses(self, project, fake_llm):
        (project / BACKUP_DIR).mkdir()
        with pytest.raises(BuildRefused, match="interrupted build"):
            _build(project, [_node("a")])
        assert fake_llm.calls == []

    def test_hand_edit_refuses_unless_forced(self, project, fake_llm):
        _, hm = _build(project, [_node("a")])
        Path("src/a.py").write_text('VALUE = "a"  # hotfix\n')

        with pytest.raises(BuildRefused, match="edited by hand"):
            _build(project, [_node("a", h="v2")], hm)
        report, _ = _build(project, [_node("a", h="v2")], hm, force=True)
        assert report.ok

    def test_failing_baseline_refuses(self, project, fake_llm):
        _, hm = _build(project, [_node("a")])
        Path("src/test_broken.py").write_text("def test_x():\n    assert False\n")

        with pytest.raises(BuildRefused, match="already fails"):
            _build(project, [_node("a", h="v2")], hm)


class TestAcceptanceTests:
    def _acceptance(self, node_id="a", body=None):
        path = Path("tests/acceptance/test_a_accept.py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            body
            or "from a import VALUE, extra\n\n\ndef test_contract():\n    assert extra() == 42\n"
        )
        node = _node(node_id)
        node.acceptance = [str(path)]
        return node, path

    def test_failing_acceptance_test_drives_repair_until_it_passes(self, project, fake_llm):
        node, acc = self._acceptance()
        fake_llm.reply(
            "a",
            "repair",
            '<file path="a.py">\nVALUE = "a"\n\n\ndef extra():\n    return 42\n</file>',
        )

        report, hm = _build(project, [node])

        assert report.ok
        plan_prompt = fake_llm.prompts[fake_llm.calls.index(("a", "plan"))]
        assert "# Acceptance tests for this spec" in plan_prompt
        assert "assert extra() == 42" in plan_prompt
        repair_prompt = fake_llm.prompts[fake_llm.calls.index(("a", "repair"))]
        assert "Hand-written acceptance tests failed" in repair_prompt
        assert str(acc) not in hm.nodes["a"].generated_files

    def test_acceptance_file_cannot_be_written_by_agents(self, project, fake_llm):
        node, acc = self._acceptance()
        original = acc.read_text()
        fake_llm.reply(
            "a", "implement", '<file path="../tests/acceptance/test_a_accept.py">\npass\n</file>'
        )

        report, _ = _build(project, [node], max_retries=0)

        assert "escapes output_dir" in report.failed["a"]
        assert acc.read_text() == original

    def test_missing_acceptance_file_refuses_build(self, project, fake_llm):
        node = _node("a")
        node.acceptance = ["tests/acceptance/nope.py"]
        with pytest.raises(BuildRefused, match="nope.py"):
            _build(project, [node])
        assert fake_llm.calls == []


class TestHandWrittenFiles:
    def test_existing_untracked_file_is_never_overwritten(self, project, fake_llm):
        Path("src").mkdir()
        Path("src/a.py").write_text("# mine\n")
        fake_llm.reply(
            "a", "repair", '<delete path="a.py"/>\n<file path="a_impl.py">\nVALUE = "a"\n</file>'
        )

        report, hm = _build(project, [_node("a")], test_command=None)

        assert report.ok
        repair_prompt = fake_llm.prompts[fake_llm.calls.index(("a", "repair"))]
        assert "a.py already exists and was not generated by specdiff" in repair_prompt
        assert Path("src/a.py").read_text() == "# mine\n"
        assert hm.nodes["a"].generated_files == ["src/a_impl.py"]


class TestInterrupt:
    def test_interrupt_removes_new_files_and_backups(self, project, fake_llm):
        with (
            patch("specdiff.agents.pipeline.run_command", side_effect=KeyboardInterrupt),
            pytest.raises(KeyboardInterrupt),
        ):
            _build(project, [_node("a")])

        assert not Path("src/a.py").exists()
        assert not (project / BACKUP_DIR).exists()


class TestSpecsWithoutTests:
    def test_spec_with_no_test_files_builds_when_suite_is_empty(self, project, fake_llm):
        fake_llm.reply("a", "plan", '<code path="a.py">types only</code><interface>\n</interface>')

        report, _ = _build(project, [_node("a")])

        assert report.ok
        assert "test" not in fake_llm.stages("a")
