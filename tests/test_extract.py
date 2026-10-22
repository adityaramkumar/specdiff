from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from specdiff.extract import CONSTITUTION_ID, _collect_source_files, generate_specs_from_code
from specdiff.parser import parse_spec_file
from specdiff.types import SpecdiffConfig


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


class TestCollectSourceFiles:
    def test_finds_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("def util(): pass")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "main.py" in paths
        assert "utils.py" in paths

    def test_finds_js_and_ts_files(self, tmp_path):
        (tmp_path / "app.js").write_text("console.log('hi')")
        (tmp_path / "types.ts").write_text("type T = string")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "app.js" in paths
        assert "types.ts" in paths

    def test_finds_yaml_and_json_files(self, tmp_path):
        (tmp_path / "config.yaml").write_text("key: value")
        (tmp_path / "schema.json").write_text('{"key": "value"}')

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "config.yaml" in paths
        assert "schema.json" in paths

    def test_ignores_non_matching_extensions(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "main.py" in paths
        assert "image.png" not in paths
        assert "binary.bin" not in paths

    def test_ignores_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lib.js").write_text("module.exports = {}")
        (tmp_path / "app.js").write_text("const x = 1")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "app.js" in paths
        assert not any("node_modules" in p for p in paths)

    def test_ignores_git_directory(self, tmp_path):
        git = tmp_path / ".git"
        git.mkdir()
        (git / "config").write_text("[core]")
        (tmp_path / "main.py").write_text("x = 1")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "main.py" in paths
        assert not any(".git" in p for p in paths)

    def test_ignores_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "module.py").write_text("cached")
        (tmp_path / "module.py").write_text("real")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "module.py" in paths
        assert not any("__pycache__" in p for p in paths)

    def test_ignores_venv_directory(self, tmp_path):
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "activate.py").write_text("# venv")
        (tmp_path / "app.py").write_text("x = 1")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert not any("venv" in p for p in paths)

    def test_handles_unicode_decode_error(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_bytes(b"\xff\xfe\x80\x81invalid utf-8")
        (tmp_path / "good.py").write_text("x = 1")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert "good.py" in paths
        assert "bad.py" not in paths

    def test_empty_directory_returns_empty_list(self, tmp_path):
        result = _collect_source_files(tmp_path)
        assert result == []

    def test_returns_relative_paths(self, tmp_path):
        subdir = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)
        (subdir / "logic.py").write_text("x = 1")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert any(os.path.join("src", "module", "logic.py") in p for p in paths)
        assert not any(str(tmp_path) in p for p in paths)

    def test_result_contains_content(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 42")

        result = _collect_source_files(tmp_path)
        entry = next(f for f in result if f["path"] == "main.py")
        assert entry["content"] == "x = 42"

    def test_ignores_specdiff_directory(self, tmp_path):
        sd = tmp_path / ".specdiff"
        sd.mkdir()
        (sd / "config.yaml").write_text("model: gemini-2.5-flash")
        (tmp_path / "app.py").write_text("x = 1")

        result = _collect_source_files(tmp_path)
        paths = [f["path"] for f in result]
        assert not any(".specdiff" in p for p in paths)


def _spec(path: str, spec_id: str, body: str = "Body.", extra: str = "") -> str:
    return (
        f'<file path="{path}">\n---\nid: {spec_id}\nversion: "1.0.0"\nstatus: approved\n'
        f"{extra}---\n\n{body}\n</file>\n"
    )


def _project(tmp_path):
    src = tmp_path / "app"
    src.mkdir()
    (src / "users.py").write_text("class User: ...\n")
    specs = tmp_path / ".specdiff"
    specs.mkdir()
    return src, specs


def _run(src, specs, replies, granularity="auto"):
    with patch("specdiff.extract.generate_content") as gen:
        gen.side_effect = [_mock_response(r) for r in replies]
        generate_specs_from_code(src, specs, SpecdiffConfig(), granularity)
    return gen


class TestExtractAuto:
    def test_writes_constitution_contracts_and_behaviors_as_drafts(self, tmp_path):
        src, specs = _project(tmp_path)
        deps = "depends_on:\n- contracts/users\n"
        _run(src, specs, [
            "Modules are flat; errors are ValueError.",
            _spec("contracts/users.spec.md", "contracts/users", "```python\nx = 'a\\nb'\n```"),
            _spec("behaviors/signup.spec.md", "behaviors/signup", extra=deps),
        ])  # fmt: skip

        constitution = parse_spec_file(specs / "constitution.spec.md")
        assert constitution.generate is False and constitution.status == "draft"
        assert "errors are ValueError" in constitution.content

        users = parse_spec_file(specs / "contracts" / "users.spec.md")
        assert users.status == "draft" and users.parent == CONSTITUTION_ID
        assert "x = 'a\\nb'" in users.content
        signup = parse_spec_file(specs / "behaviors" / "signup.spec.md")
        assert signup.depends_on == ["contracts/users"]

    def test_contract_ids_are_listed_in_behavior_prompt(self, tmp_path):
        src, specs = _project(tmp_path)
        gen = _run(src, specs, ["c", _spec("contracts/users.spec.md", "contracts/users"), ""])
        assert "- contracts/users" in gen.call_args_list[2].kwargs["contents"]

    def test_existing_specs_are_never_overwritten(self, tmp_path):
        src, specs = _project(tmp_path)
        (specs / "contracts").mkdir()
        (specs / "contracts" / "users.spec.md").write_text("mine")
        (specs / "constitution.spec.md").write_text("mine too")
        gen = _run(src, specs, [_spec("contracts/users.spec.md", "contracts/users"), ""])

        assert (specs / "contracts" / "users.spec.md").read_text() == "mine"
        assert (specs / "constitution.spec.md").read_text() == "mine too"
        assert gen.call_count == 2

    def test_paths_outside_specs_dir_are_rejected(self, tmp_path):
        src, specs = _project(tmp_path)
        _run(src, specs, ["c", _spec("../evil.spec.md", "evil"), ""])
        assert not (tmp_path / "evil.spec.md").exists()

    def test_missing_extension_added_and_blocks_without_id_skipped(self, tmp_path):
        src, specs = _project(tmp_path)
        no_id = '<file path="contracts/x.spec.md">\n---\nversion: "1"\n---\nx\n</file>'
        _run(src, specs, ["c", _spec("contracts/orders", "contracts/orders") + no_id, ""])
        assert (specs / "contracts" / "orders.spec.md").exists()
        assert not (specs / "contracts" / "x.spec.md").exists()

    def test_constitution_failure_still_extracts_without_parent(self, tmp_path):
        src, specs = _project(tmp_path)
        with patch("specdiff.extract.generate_content") as gen:
            gen.side_effect = [
                RuntimeError("timeout"),
                _mock_response(_spec("contracts/users.spec.md", "contracts/users")),
                _mock_response(""),
            ]
            generate_specs_from_code(src, specs, SpecdiffConfig())
        assert parse_spec_file(specs / "contracts" / "users.spec.md").parent is None


class TestExtractFileByFile:
    def test_one_spec_per_file(self, tmp_path):
        src, specs = _project(tmp_path)
        (src / "orders.py").write_text("x = 1\n")
        gen = _run(src, specs, [
            "c",
            _spec("behaviors/users.spec.md", "behaviors/users"),
            _spec("behaviors/orders.spec.md", "behaviors/orders"),
        ], granularity="file")  # fmt: skip
        assert gen.call_count == 3
        assert (specs / "behaviors" / "users.spec.md").exists()
        assert (specs / "behaviors" / "orders.spec.md").exists()
