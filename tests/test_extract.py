from __future__ import annotations

import os

from specdiff.extract import _collect_source_files


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
