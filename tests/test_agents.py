from __future__ import annotations

import pytest

from specdiff.agents import fileblocks, stages
from specdiff.agents.context import NodeContext, render
from specdiff.build.files import strip_header, traceability_header
from specdiff.types import SpecNode


def _node(id="auth/login", content="Users log in.") -> SpecNode:
    return SpecNode(id=id, version="1.0.0", status="approved", hash="h", content=content,
                    file_path="x.spec.md")  # fmt: skip


class TestFileBlocks:
    def test_contents_are_verbatim(self):
        text = 'Here you go:\n<file path="a.py">\nx = "line\\nbreak"\n</file>\n'
        assert fileblocks.parse(text).files == {"a.py": 'x = "line\\nbreak"\n'}

    def test_unchanged_and_delete_markers(self):
        blocks = fileblocks.parse('<unchanged path="a.py"/>\n<delete path="b.py" />')
        assert blocks.unchanged == ["a.py"] and blocks.deleted == ["b.py"]

    def test_render_round_trips(self):
        files = {"a.py": "x = 1\n", "dir/b.ts": "export const y = 2;\n"}
        assert fileblocks.parse(fileblocks.render(files)).files == files


class TestContext:
    def test_sections_in_order_with_project_facts(self):
        ctx = NodeContext(
            node=_node(),
            language="python",
            output_dir="src",
            ancestors=[_node("constitution", "Errors are JSON.")],
            deps=[_node("contracts/users", "User has an email.")],
            dep_files={"users.py": "class User: ...\n"},
            others={"billing.py": "billing/core"},
            test_command="pytest",
        )
        prompt = render(ctx)
        order = ["# Project", "constitution", "contracts/users", "Dependency code",
                 "billing.py (owned by `billing/core`)", "# Spec `auth/login`"]  # fmt: skip
        positions = [prompt.index(marker) for marker in order]
        assert positions == sorted(positions)
        assert "Tests run from the project root with: `pytest`" in prompt
        assert "never use relative imports" in prompt


class TestStageParsing:
    def test_plan(self, monkeypatch):
        reply = (
            '<code path="a.py">does a</code>\n<test path="test_a.py">tests a</test>\n'
            "<interface>\ndef a() -> int: ...\n</interface>"
        )
        monkeypatch.setattr(stages, "complete", lambda *a: stages.LLMResponse(reply, 5, 2))
        usage = stages.Usage()
        ctx = NodeContext(node=_node(), language="python", output_dir="src")
        plan = stages.plan(ctx, "system", "m", usage)

        assert plan.code == {"a.py": "does a"} and plan.tests == {"test_a.py": "tests a"}
        assert "def a() -> int" in plan.interface
        assert (usage.calls, usage.input_tokens, usage.output_tokens) == (1, 5, 2)

    def test_plan_without_files_is_an_error(self, monkeypatch):
        monkeypatch.setattr(stages, "complete", lambda *a: stages.LLMResponse("I can't."))
        ctx = NodeContext(node=_node(), language="python", output_dir="src")
        with pytest.raises(stages.StageError, match="no production files"):
            stages.plan(ctx, "s", "m", stages.Usage())

    @pytest.mark.parametrize(("verdict", "passed"), [("PASS", True), ("fail", False)])
    def test_review_verdict(self, monkeypatch, verdict, passed):
        reply = f"<verdict>{verdict}</verdict>\n<feedback>\nnotes\n</feedback>"
        monkeypatch.setattr(stages, "complete", lambda *a: stages.LLMResponse(reply))
        ctx = NodeContext(node=_node(), language="python", output_dir="src")
        result = stages.review(ctx, stages.Plan(code={"a.py": ""}), {}, "s", "m", stages.Usage())
        assert result == (passed, "notes")

    def test_review_accepts_legacy_json_reply(self, monkeypatch):
        reply = '{"passed": false, "feedback": ["a", "b"]}'
        monkeypatch.setattr(stages, "complete", lambda *a: stages.LLMResponse(reply))
        ctx = NodeContext(node=_node(), language="python", output_dir="src")
        result = stages.review(ctx, stages.Plan(code={"a.py": ""}), {}, "s", "m", stages.Usage())
        assert result == (False, "a\nb")


class TestHeaders:
    @pytest.mark.parametrize("ext", [".py", ".ts", ".css", ".html"])
    def test_header_round_trips(self, tmp_path, ext):
        path = tmp_path / f"f{ext}"
        body = "first line\nsecond\n"
        assert strip_header(traceability_header(path, _node()) + body) == body

    def test_json_gets_no_header(self, tmp_path):
        assert traceability_header(tmp_path / "data.json", _node()) == ""

    def test_old_four_line_header_is_stripped_but_comments_kept(self):
        old = (
            "# generated_from: a\n# spec_hash: h\n# generated_at: t\n# agent: impl\n# note\nx = 1\n"
        )
        assert strip_header(old) == "# note\nx = 1\n"
