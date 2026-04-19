from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from specdiff.agents.swarm import REQUIRED_SKILLS
from specdiff.graph import build_graph
from specdiff.runner import (
    BACKUP_DIR,
    _traceability_header,
    backup,
    clean_backups,
    execute_swarm_cascade,
    restore,
    run_tests,
)
from specdiff.types import (
    FilePlan,
    HashMap,
    HashMapEntry,
    SpecdiffConfig,
    SpecNode,
    SwarmResult,
)


def _make_node(node_id: str = "test/example", spec_hash: str = "abc123") -> SpecNode:
    return SpecNode(
        id=node_id,
        version="1.0.0",
        status="approved",
        hash=spec_hash,
        content="## Example",
        file_path=f".specdiff/{node_id}.spec.md",
    )


def _swarm_ok(node, config, specs_dir, dep_specs=None):
    return SwarmResult(
        file_plan=FilePlan(files={f"{node.id.replace('/', '_')}.py": "impl"}),
        generated_files={f"{node.id.replace('/', '_')}.py": f"# {node.id}\n"},
        generated_tests={},
        review_passed=True,
        review_feedback="ok",
    )


def _swarm_review_fail(node, config, specs_dir, dep_specs=None):
    return SwarmResult(
        file_plan=FilePlan(files={"out.py": "impl"}),
        generated_files={"out.py": "# code\n"},
        generated_tests={},
        review_passed=False,
        review_feedback="spec mismatch",
    )


# ---------------------------------------------------------------------------
# backup / restore / clean_backups
# ---------------------------------------------------------------------------


class TestBackup:
    def test_copies_existing_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        src_file = tmp_path / "src" / "main.py"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("print('hello')")

        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()

        backup(["src/main.py"], specs_dir)

        backed = specs_dir / BACKUP_DIR / "src" / "main.py"
        assert backed.exists()
        assert backed.read_text() == "print('hello')"

    def test_skips_missing_files(self, tmp_path):
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()

        backup(["nonexistent/file.py"], specs_dir)

        assert not (specs_dir / BACKUP_DIR).exists()

    def test_backs_up_multiple_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for name in ["a.py", "b.py"]:
            (tmp_path / name).write_text(f"# {name}")

        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()

        backup(["a.py", "b.py"], specs_dir)

        assert (specs_dir / BACKUP_DIR / "a.py").exists()
        assert (specs_dir / BACKUP_DIR / "b.py").exists()


class TestRestore:
    def test_restores_backed_up_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()

        backed = specs_dir / BACKUP_DIR / "src" / "main.py"
        backed.parent.mkdir(parents=True)
        backed.write_text("original content")

        actual = tmp_path / "src" / "main.py"
        actual.parent.mkdir(parents=True)
        actual.write_text("new content")

        restore(["src/main.py"], specs_dir)

        assert actual.read_text() == "original content"

    def test_deletes_new_file_with_no_backup(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()

        actual = tmp_path / "src" / "new_file.py"
        actual.parent.mkdir(parents=True)
        actual.write_text("generated content")

        restore(["src/new_file.py"], specs_dir)

        assert not actual.exists()

    def test_calls_clean_backups_after_restore(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        backup_root = specs_dir / BACKUP_DIR
        backup_root.mkdir()

        restore([], specs_dir)

        assert not backup_root.exists()


class TestCleanBackups:
    def test_removes_backup_dir(self, tmp_path):
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        backup_root = specs_dir / BACKUP_DIR
        backup_root.mkdir()
        (backup_root / "some_file.py").write_text("content")

        clean_backups(specs_dir)

        assert not backup_root.exists()

    def test_noop_when_no_backup_dir(self, tmp_path):
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        clean_backups(specs_dir)


# ---------------------------------------------------------------------------
# run_tests
# ---------------------------------------------------------------------------


class TestRunTests:
    def test_no_command_returns_true(self):
        config = SpecdiffConfig(test_command=None)
        passed, output = run_tests(config)
        assert passed is True
        assert output == ""

    @patch("specdiff.runner.subprocess.run")
    def test_passing_command_returns_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="all good", stderr="")
        config = SpecdiffConfig(test_command="pytest")
        passed, _ = run_tests(config)
        assert passed is True

    @patch("specdiff.runner.subprocess.run")
    def test_failing_command_returns_false(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="FAILED")
        config = SpecdiffConfig(test_command="pytest")
        passed, _ = run_tests(config)
        assert passed is False

    @patch("specdiff.runner.subprocess.run")
    def test_output_combines_stdout_and_stderr(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="out", stderr="err")
        config = SpecdiffConfig(test_command="pytest")
        _, output = run_tests(config)
        assert "out" in output
        assert "err" in output


# ---------------------------------------------------------------------------
# _traceability_header
# ---------------------------------------------------------------------------


class TestTraceabilityHeader:
    def _node(self, nid: str = "auth/login", spec_hash: str = "h123") -> SpecNode:
        return SpecNode(
            id=nid,
            version="1.0.0",
            status="approved",
            hash=spec_hash,
            content="",
            file_path=f".specdiff/{nid}.spec.md",
        )

    def test_python_uses_hash_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "module.py", self._node(), "impl")
        assert header.startswith("# generated_from:")

    def test_js_uses_line_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "app.js", self._node(), "impl")
        assert header.startswith("// generated_from:")

    def test_ts_uses_line_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "app.ts", self._node(), "impl")
        assert header.startswith("// generated_from:")

    def test_tsx_uses_line_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "Component.tsx", self._node(), "impl")
        assert header.startswith("// generated_from:")

    def test_java_uses_line_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "Main.java", self._node(), "impl")
        assert header.startswith("// generated_from:")

    def test_go_uses_line_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "main.go", self._node(), "impl")
        assert header.startswith("// generated_from:")

    def test_css_uses_block_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "styles.css", self._node(), "impl")
        assert header.startswith("/*")
        assert "*/" in header

    def test_scss_uses_block_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "styles.scss", self._node(), "impl")
        assert header.startswith("/*")

    def test_sql_uses_block_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "schema.sql", self._node(), "impl")
        assert header.startswith("/*")

    def test_html_uses_xml_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "index.html", self._node(), "impl")
        assert header.startswith("<!--")
        assert "-->" in header

    def test_xml_uses_xml_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "config.xml", self._node(), "impl")
        assert header.startswith("<!--")

    def test_md_uses_xml_comments(self, tmp_path):
        header = _traceability_header(tmp_path / "docs.md", self._node(), "impl")
        assert header.startswith("<!--")

    def test_unknown_extension_falls_back_to_hash(self, tmp_path):
        header = _traceability_header(tmp_path / "file.xyz", self._node(), "impl")
        assert header.startswith("# generated_from:")

    def test_header_includes_node_id(self, tmp_path):
        header = _traceability_header(tmp_path / "mod.py", self._node("auth/login"), "impl")
        assert "auth/login" in header

    def test_header_includes_spec_hash(self, tmp_path):
        header = _traceability_header(tmp_path / "mod.py", self._node(spec_hash="deadbeef"), "impl")
        assert "deadbeef" in header

    def test_header_includes_agent_name(self, tmp_path):
        header = _traceability_header(tmp_path / "mod.py", self._node(), "testing-agent")
        assert "testing-agent" in header


# ---------------------------------------------------------------------------
# execute_swarm_cascade
# ---------------------------------------------------------------------------


def _setup_skills(specs_dir: Path) -> None:
    skills_dir = specs_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_SKILLS:
        (skills_dir / f"{name}.skill.md").write_text(f"Skill for {name}")


class TestExecuteSwarmCascade:
    def test_baseline_test_failure_aborts(self, tmp_path):
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap(
            nodes={
                node.id: HashMapEntry(
                    spec_hash="old", generated_files=["out.py"], generated_at=""
                )
            }
        )
        config = SpecdiffConfig(test_command="pytest")

        with patch("specdiff.runner.run_tests", return_value=(False, "FAILED")) as mock_tests:
            ok = execute_swarm_cascade([node], config, map_, graph, specs_dir)

        assert ok is False
        mock_tests.assert_called_once()

    def test_swarm_exception_triggers_rollback(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap()
        config = SpecdiffConfig()

        with patch("specdiff.runner.run_swarm", side_effect=RuntimeError("LLM timeout")):
            ok = execute_swarm_cascade([node], config, map_, graph, specs_dir)

        assert ok is False
        assert node.id not in map_.nodes

    def test_post_generation_test_failure_rolls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap()
        config = SpecdiffConfig(test_command="pytest")

        with (
            patch("specdiff.runner.run_swarm", side_effect=_swarm_ok),
            patch("specdiff.runner.run_tests", return_value=(False, "5 failed")),
        ):
            ok = execute_swarm_cascade([node], config, map_, graph, specs_dir)

        assert ok is False
        assert node.id not in map_.nodes

    def test_post_generation_test_failure_removes_generated_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap()
        config = SpecdiffConfig(test_command="pytest")

        with (
            patch("specdiff.runner.run_swarm", side_effect=_swarm_ok),
            patch("specdiff.runner.run_tests", return_value=(False, "failed")),
        ):
            execute_swarm_cascade([node], config, map_, graph, specs_dir)

        generated = tmp_path / "src" / "test_example.py"
        assert not generated.exists()

    def test_skip_review_continues_on_review_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap()
        config = SpecdiffConfig()

        with (
            patch("specdiff.runner.run_swarm", side_effect=_swarm_review_fail),
            patch("specdiff.runner.run_tests", return_value=(True, "")),
        ):
            ok = execute_swarm_cascade([node], config, map_, graph, specs_dir, skip_review=True)

        assert ok is True
        assert node.id in map_.nodes

    def test_review_failure_without_skip_aborts_and_rolls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap()
        config = SpecdiffConfig()

        with patch("specdiff.runner.run_swarm", side_effect=_swarm_review_fail):
            ok = execute_swarm_cascade([node], config, map_, graph, specs_dir, skip_review=False)

        assert ok is False
        assert node.id not in map_.nodes

    def test_success_updates_hashmap(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node = _make_node()
        graph = build_graph([node])
        map_ = HashMap()
        config = SpecdiffConfig()

        with (
            patch("specdiff.runner.run_swarm", side_effect=_swarm_ok),
            patch("specdiff.runner.run_tests", return_value=(True, "")),
        ):
            ok = execute_swarm_cascade([node], config, map_, graph, specs_dir)

        assert ok is True
        assert node.id in map_.nodes
        assert map_.nodes[node.id].spec_hash == node.hash

    def test_multi_node_cascade_updates_all(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node_a = _make_node("contracts/api", "hash_a")
        node_b = SpecNode(
            id="behaviors/login",
            version="1.0.0",
            status="approved",
            hash="hash_b",
            content="## Login",
            file_path=".specdiff/behaviors/login.spec.md",
            depends_on=["contracts/api"],
        )
        graph = build_graph([node_a, node_b])
        map_ = HashMap()
        config = SpecdiffConfig()

        with (
            patch("specdiff.runner.run_swarm", side_effect=_swarm_ok),
            patch("specdiff.runner.run_tests", return_value=(True, "")),
        ):
            ok = execute_swarm_cascade([node_a, node_b], config, map_, graph, specs_dir)

        assert ok is True
        assert "contracts/api" in map_.nodes
        assert "behaviors/login" in map_.nodes

    def test_exception_on_second_node_does_not_update_first(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()
        node_a = _make_node("contracts/api", "hash_a")
        node_b = _make_node("behaviors/login", "hash_b")
        graph = build_graph([node_a, node_b])
        map_ = HashMap()
        config = SpecdiffConfig()

        call_count = {"n": 0}

        def _fail_on_second(node, config, specs_dir, dep_specs=None):
            call_count["n"] += 1
            if call_count["n"] > 1:
                raise RuntimeError("second node failed")
            return _swarm_ok(node, config, specs_dir, dep_specs)

        with patch("specdiff.runner.run_swarm", side_effect=_fail_on_second):
            ok = execute_swarm_cascade([node_a, node_b], config, map_, graph, specs_dir)

        assert ok is False
        assert "contracts/api" not in map_.nodes
        assert "behaviors/login" not in map_.nodes
