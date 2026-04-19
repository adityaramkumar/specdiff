from __future__ import annotations

from specdiff.agents.architect import format_architect_prompt, parse_file_plan
from specdiff.types import SpecNode


def _make_node(
    nid: str = "test/example",
    content: str = "## Example\n\nDo the thing.",
) -> SpecNode:
    return SpecNode(
        id=nid,
        version="1.0.0",
        status="approved",
        hash="abc123",
        content=content,
        file_path=f".specdiff/{nid}.spec.md",
    )


class TestFormatArchitectPrompt:
    def test_includes_spec_id(self):
        prompt = format_architect_prompt(_make_node("auth/login"))
        assert "auth/login" in prompt

    def test_includes_spec_version(self):
        prompt = format_architect_prompt(_make_node())
        assert "1.0.0" in prompt

    def test_includes_spec_content(self):
        prompt = format_architect_prompt(_make_node(content="## Login\n\nValidate JWT."))
        assert "Validate JWT" in prompt

    def test_no_deps_shows_none(self):
        prompt = format_architect_prompt(_make_node(), dep_specs=None)
        assert "none" in prompt

    def test_empty_deps_shows_none(self):
        prompt = format_architect_prompt(_make_node(), dep_specs=[])
        assert "none" in prompt

    def test_includes_dependency_id(self):
        dep = _make_node("contracts/schema", "## Schema\n\nUser has id and email.")
        prompt = format_architect_prompt(_make_node(), dep_specs=[dep])
        assert "contracts/schema" in prompt

    def test_includes_dependency_content_snippet(self):
        dep = _make_node("contracts/schema", "## Schema\n\nUser has id and email.")
        prompt = format_architect_prompt(_make_node(), dep_specs=[dep])
        assert "Schema" in prompt

    def test_multiple_deps_all_included(self):
        dep1 = _make_node("contracts/a", "Contract A content")
        dep2 = _make_node("contracts/b", "Contract B content")
        prompt = format_architect_prompt(_make_node(), dep_specs=[dep1, dep2])
        assert "contracts/a" in prompt
        assert "contracts/b" in prompt

    def test_instructs_json_output(self):
        prompt = format_architect_prompt(_make_node())
        assert "JSON" in prompt


class TestParseFilePlan:
    def test_valid_json_object(self):
        raw = '{"src/main.py": "entry point", "src/utils.py": "helpers"}'
        plan = parse_file_plan(raw)
        assert "src/main.py" in plan.files
        assert plan.files["src/main.py"] == "entry point"

    def test_fenced_json(self):
        raw = '```json\n{"src/main.py": "entry point"}\n```'
        plan = parse_file_plan(raw)
        assert "src/main.py" in plan.files

    def test_invalid_json_returns_empty_plan(self):
        plan = parse_file_plan("this is not valid json at all")
        assert plan.files == {}

    def test_empty_object_returns_empty_plan(self):
        plan = parse_file_plan("{}")
        assert plan.files == {}

    def test_multiple_files(self):
        import json
        data = {
            "src/auth.py": "authentication logic",
            "src/models.py": "data models",
            "tests/test_auth.py": "auth tests",
        }
        plan = parse_file_plan(json.dumps(data))
        assert len(plan.files) == 3
        assert "src/auth.py" in plan.files
