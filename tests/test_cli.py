from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specdiff.cli import cli
from specdiff.types import ReviewResult
from tests.fake_llm import FakeLLM

LLM = "specdiff.agents.stages.complete"


def _write_spec(
    root: Path,
    rel_path: str,
    spec_id: str,
    depends_on: list[str] | None = None,
    status: str = "approved",
) -> None:
    dep_line = ""
    if depends_on:
        items = "\n".join(f"  - {d}" for d in depends_on)
        dep_line = f"depends_on:\n{items}\n"
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = f"---\nid: {spec_id}\nversion: '1.0.0'\nstatus: {status}\n{dep_line}---\n"
    path.write_text(f"{fm}\nSpec body for {spec_id}\n")


def _setup_project(tmp_path: Path, specs: list[dict], *, with_skill: bool = False) -> Path:
    """Create a minimal project with .specdiff/config.yaml, skill files, and spec files."""
    specdiff_dir = tmp_path / ".specdiff"
    specdiff_dir.mkdir()
    (specdiff_dir / "config.yaml").write_text(
        "model: gemini-3.1-flash-lite-preview\noutput_dir: src\nspecs_dir: .specdiff\n"
    )

    skills_dir = specdiff_dir / "skills"
    skills_dir.mkdir()
    if with_skill:
        (skills_dir / "spec-eval.skill.md").write_text("## Role\nYou review specs.\n")

    for s in specs:
        _write_spec(specdiff_dir, s["path"], s["id"], s.get("depends_on"))
    return tmp_path


def _mock_review_pass(node, skill, config):
    return ReviewResult(passed=True, feedback="All criteria met.")


def _mock_review_fail(node, skill, config):
    return ReviewResult(
        passed=False,
        feedback="Vague error handling.",
        proposed_revision="## Revised\n\nReturn HTTP 500.",
    )


class TestStatus:
    def test_no_specs(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["status"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "No spec files found" in result.output

    def test_shows_new(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["status"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "auth/login" in result.output
        assert "new" in result.output

    def test_shows_stale(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        hm_data = {
            "auth/login": {
                "spec_hash": "oldhash_that_wont_match",
                "generated_files": [],
                "generated_at": "",
            }
        }
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["status"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "stale" in result.output

    def test_shows_current(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        from specdiff.parser import parse_spec_file

        node = parse_spec_file(proj / ".specdiff" / "behaviors" / "auth" / "login.spec.md")
        hm_data = {node.id: {"spec_hash": node.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["status"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "current" in result.output


class TestBuild:
    def test_no_specs(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No spec files found" in result.output

    def test_invalid_node_id_raises(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "nonexistent/spec"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_build_single_node_id(self, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "behaviors/auth/login.spec.md", "id": "auth/login"},
                {"path": "behaviors/auth/signup.spec.md", "id": "auth/signup"},
            ],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "auth/login"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert [n for n, stage in fake_llm.calls if stage == "plan"] == ["auth/login"]

    def test_no_review_flag_skips_review_stage(self, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        fake_llm.reply("auth/login", "review", "<verdict>fail</verdict><feedback>x</feedback>")
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "--no-review"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "review" not in fake_llm.stages("auth/login")

    @patch("specdiff.cli.review_spec", side_effect=_mock_review_fail)
    def test_build_review_before_build_aborts_on_fail(self, mock_review, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        (proj / ".specdiff" / "config.yaml").write_text(
            "model: gemini-2.5-flash\n"
            "output_dir: src\n"
            "specs_dir: .specdiff\n"
            "review_before_build: true\n"
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"])
        assert result.exit_code != 0
        assert "failed review" in result.output

    def test_updates_hashmap(self, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "Built 1, failed 0, skipped 0" in result.output

        hm_path = proj / ".specdiff" / "hash-map.json"
        assert hm_path.exists()
        data = json.loads(hm_path.read_text())
        assert "auth/login" in data

    def test_idempotent(self, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            runner.invoke(cli, ["build"], catch_exceptions=False)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "Everything is up to date" in result.output

    def test_writes_language_aware_traceability_headers(self, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        fake_llm.reply("auth/login", "plan", '<code path="auth/login.ts">x</code>')
        fake_llm.reply(
            "auth/login",
            "implement",
            '<file path="auth/login.ts">\nexport function login() {}\n</file>',
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        generated = proj / "src" / "auth" / "login.ts"
        assert generated.read_text().startswith("// generated_from: auth/login")

    def test_review_failure_after_repairs_fails_the_build(self, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        fail = "<verdict>fail</verdict><feedback>missing lockout</feedback>"
        fake_llm.reply("auth/login", "review", fail, fail, fail)
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"])

        assert result.exit_code == 1
        assert "missing lockout" in result.output
        assert fake_llm.stages("auth/login").count("repair") == 2
        assert not (proj / "src" / "auth_login.py").exists()
        hm_path = proj / ".specdiff" / "hash-map.json"
        assert not hm_path.exists() or "auth/login" not in json.loads(hm_path.read_text())


class TestBuildDryRun:
    def test_dry_run_shows_plan_without_building(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "contracts/api/users.spec.md", "id": "contracts/api/users"},
                {
                    "path": "behaviors/auth/login.spec.md",
                    "id": "behaviors/auth/login",
                    "depends_on": ["contracts/api/users"],
                },
            ],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "--dry-run"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "Would build 2 node(s)" in result.output
        assert "contracts/api/users" in result.output
        assert "behaviors/auth/login" in result.output
        assert "[new]" in result.output
        hm_path = proj / ".specdiff" / "hash-map.json"
        assert not hm_path.exists()

    def test_dry_run_shows_cascade_reason(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "contracts/api/users.spec.md", "id": "contracts/api/users"},
                {
                    "path": "behaviors/auth/login.spec.md",
                    "id": "behaviors/auth/login",
                    "depends_on": ["contracts/api/users"],
                },
            ],
        )
        from specdiff.parser import parse_spec_file

        node = parse_spec_file(proj / ".specdiff" / "behaviors" / "auth" / "login.spec.md")
        hm_data = {node.id: {"spec_hash": node.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "--dry-run"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "contracts/api/users" in result.output
        assert "behaviors/auth/login  [contracts/api/users changed]" in result.output

    def test_dry_run_up_to_date_exits_cleanly(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        from specdiff.parser import parse_spec_file

        node = parse_spec_file(proj / ".specdiff" / "behaviors" / "auth" / "login.spec.md")
        hm_data = {node.id: {"spec_hash": node.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "--dry-run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_dry_run_does_not_call_swarm(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with (
            patch(LLM) as mock_llm,
            runner.isolated_filesystem(temp_dir=tmp_path),
        ):
            os.chdir(proj)
            runner.invoke(cli, ["build", "--dry-run"], catch_exceptions=False)
        mock_llm.assert_not_called()


class TestImpact:
    def test_no_specs(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No spec files found" in result.output

    def test_impact_single_node_id(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "contracts/schema.spec.md", "id": "contracts/schema"},
                {"path": "behaviors/login.spec.md", "id": "auth/login"},
            ],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact", "contracts/schema"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "contracts/schema" in result.output

    def test_impact_leaf_node_has_no_blast_radius(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
        )
        from specdiff.parser import parse_spec_file

        node = parse_spec_file(proj / ".specdiff" / "behaviors" / "login.spec.md")
        hm_data = {node.id: {"spec_hash": node.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact", "auth/login"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Nothing depends on auth/login" in result.output

    def test_shows_cascade(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "contracts/schema.spec.md", "id": "contracts/schema"},
                {
                    "path": "behaviors/auth/login.spec.md",
                    "id": "auth/login",
                    "depends_on": ["contracts/schema"],
                },
            ],
        )
        from specdiff.parser import parse_spec_file

        contract = parse_spec_file(proj / ".specdiff" / "contracts" / "schema.spec.md")
        hm_data = {
            contract.id: {
                "spec_hash": contract.hash,
                "generated_files": [],
                "generated_at": "",
            }
        }
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "auth/login" in result.output
        assert "node(s) will be rebuilt" in result.output

    def test_up_to_date(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        from specdiff.parser import parse_spec_file

        node = parse_spec_file(proj / ".specdiff" / "behaviors" / "auth" / "login.spec.md")
        hm_data = {node.id: {"spec_hash": node.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "up to date" in result.output


class TestReview:
    def test_no_specs(self, tmp_path):
        proj = _setup_project(tmp_path, [], with_skill=True)
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No spec files found" in result.output

    def test_all_approved(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "already approved" in result.output

    def test_missing_skill_raises(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=False,
        )
        _write_spec(proj / ".specdiff", "behaviors/login.spec.md", "auth/login", status="draft")
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review"])
        assert result.exit_code != 0

    def test_invalid_node_id_raises(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review", "nonexistent/spec"])
        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("specdiff.cli.review_spec", side_effect=_mock_review_pass)
    def test_review_single_node_id(self, mock_review, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "behaviors/login.spec.md", "id": "auth/login"},
                {"path": "behaviors/signup.spec.md", "id": "auth/signup"},
            ],
            with_skill=True,
        )
        _write_spec(proj / ".specdiff", "behaviors/login.spec.md", "auth/login", status="draft")
        _write_spec(proj / ".specdiff", "behaviors/signup.spec.md", "auth/signup", status="draft")

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review", "auth/login"], catch_exceptions=False)
        assert result.exit_code == 0
        assert mock_review.call_count == 1

    @patch("specdiff.cli.review_spec", side_effect=_mock_review_pass)
    def test_review_pass(self, mock_review, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        _write_spec(
            proj / ".specdiff",
            "behaviors/login.spec.md",
            "auth/login",
            status="draft",
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "PASSED" in result.output

    @patch("specdiff.cli.review_spec", side_effect=_mock_review_fail)
    def test_review_fail_writes_proposal(self, mock_review, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        _write_spec(
            proj / ".specdiff",
            "behaviors/login.spec.md",
            "auth/login",
            status="draft",
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["review"])

        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Suggested revision" in result.output
        proposed = proj / ".specdiff" / "proposed" / "auth_login.spec.md"
        assert proposed.exists()

    @patch("specdiff.cli.review_spec", side_effect=_mock_review_pass)
    def test_build_reviews_all_stale_specs_when_enabled(self, mock_review, fake_llm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        (proj / ".specdiff" / "config.yaml").write_text(
            "model: gemini-2.5-flash\n"
            "output_dir: src\n"
            "specs_dir: .specdiff\n"
            "review_before_build: true\n"
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        mock_review.assert_called_once()


class TestInit:
    def test_creates_directory_structure(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
        assert (tmp_path / ".specdiff").is_dir()
        assert (tmp_path / ".specdiff" / "config.yaml").exists()
        assert (tmp_path / ".specdiff" / "skills" / "README.md").exists()
        assert (tmp_path / ".specdiff" / "behaviors" / "hello.spec.md").exists()
        assert "test_command:" in (tmp_path / ".specdiff" / "config.yaml").read_text()

    def test_init_message(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["init"], catch_exceptions=False)
        assert "Created .specdiff/" in result.output

    def test_config_contains_model(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            runner.invoke(cli, ["init"], catch_exceptions=False)
        config_text = (tmp_path / ".specdiff" / "config.yaml").read_text()
        assert "model:" in config_text

    def test_already_exists_is_noop(self, tmp_path):
        (tmp_path / ".specdiff").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "already exists" in result.output


class TestExtract:
    def test_not_initialized_exits(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["extract"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "not initialized" in result.output

    def test_missing_source_dir_exits_nonzero(self, tmp_path):
        (tmp_path / ".specdiff").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["extract", "--source", "totally_missing_dir"])
        assert result.exit_code == 1
        assert "does not exist" in result.output


class TestClean:
    def _write_hash_map(self, proj: Path, entries: dict) -> None:
        (proj / ".specdiff" / "hash-map.json").write_text(json.dumps(entries))

    def test_nothing_to_clean(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["clean", "--yes"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Nothing to clean" in result.output

    def test_cleans_all_nodes(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        gen_file = proj / "src" / "auth_login.py"
        gen_file.parent.mkdir(parents=True, exist_ok=True)
        gen_file.write_text("# generated\n")
        self._write_hash_map(
            proj,
            {
                "auth/login": {
                    "spec_hash": "abc123",
                    "generated_files": [str(gen_file)],
                    "generated_at": "",
                }
            },
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["clean", "--yes"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "auth/login" in result.output
        assert "1 file(s) removed" in result.output
        assert not gen_file.exists()
        hm_data = json.loads((proj / ".specdiff" / "hash-map.json").read_text())
        assert "auth/login" not in hm_data

    def test_cleans_single_node(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "behaviors/auth/login.spec.md", "id": "auth/login"},
                {"path": "behaviors/auth/signup.spec.md", "id": "auth/signup"},
            ],
        )
        login_file = proj / "src" / "auth_login.py"
        login_file.parent.mkdir(parents=True, exist_ok=True)
        login_file.write_text("# generated\n")
        self._write_hash_map(
            proj,
            {
                "auth/login": {
                    "spec_hash": "abc",
                    "generated_files": [str(login_file)],
                    "generated_at": "",
                },
                "auth/signup": {
                    "spec_hash": "def",
                    "generated_files": [],
                    "generated_at": "",
                },
            },
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["clean", "--yes", "auth/login"], catch_exceptions=False)

        assert result.exit_code == 0
        assert not login_file.exists()
        hm_data = json.loads((proj / ".specdiff" / "hash-map.json").read_text())
        assert "auth/login" not in hm_data
        assert "auth/signup" in hm_data

    def test_unknown_node_id_errors(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        self._write_hash_map(
            proj,
            {
                "auth/login": {
                    "spec_hash": "abc",
                    "generated_files": [],
                    "generated_at": "",
                }
            },
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["clean", "--yes", "nonexistent/node"])
        assert result.exit_code != 0
        assert "nonexistent/node" in result.output

    def test_missing_files_are_skipped_gracefully(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        self._write_hash_map(
            proj,
            {
                "auth/login": {
                    "spec_hash": "abc",
                    "generated_files": ["/tmp/does_not_exist_xyz.py"],
                    "generated_at": "",
                }
            },
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["clean", "--yes"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "0 file(s) removed" in result.output


class TestValidate:
    def test_no_specs(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["validate"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No spec files found" in result.output

    def test_valid_graph_passes(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "contracts/api/users.spec.md", "id": "contracts/api/users"},
                {
                    "path": "behaviors/auth/login.spec.md",
                    "id": "behaviors/auth/login",
                    "depends_on": ["contracts/api/users"],
                },
            ],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["validate"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No issues found" in result.output
        assert "2 spec(s)" in result.output

    def test_missing_depends_on_ref(self, tmp_path):
        proj = _setup_project(
            tmp_path,
            [
                {
                    "path": "behaviors/auth/login.spec.md",
                    "id": "behaviors/auth/login",
                    "depends_on": ["contracts/api/nonexistent"],
                }
            ],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "contracts/api/nonexistent" in result.output
        assert "not found" in result.output

    def test_missing_parent_ref(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        spec_path = proj / ".specdiff" / "behaviors" / "auth" / "login.spec.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            "---\nid: behaviors/auth/login\nversion: '1.0.0'\nstatus: approved\n"
            "parent: ghost/parent\n---\n\nSpec body.\n"
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "ghost/parent" in result.output
        assert "not found" in result.output

    def test_circular_dependency_detected(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        specdiff = proj / ".specdiff"
        a = specdiff / "behaviors" / "a.spec.md"
        b = specdiff / "behaviors" / "b.spec.md"
        a.parent.mkdir(parents=True, exist_ok=True)
        a.write_text(
            "---\nid: behaviors/a\nversion: '1.0.0'\nstatus: approved\n"
            "depends_on:\n  - behaviors/b\n---\n\nSpec A.\n"
        )
        b.write_text(
            "---\nid: behaviors/b\nversion: '1.0.0'\nstatus: approved\n"
            "depends_on:\n  - behaviors/a\n---\n\nSpec B.\n"
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "Circular" in result.output

    def test_multiple_errors_all_reported(self, tmp_path):
        proj = _setup_project(tmp_path, [])
        specdiff = proj / ".specdiff"
        (specdiff / "behaviors").mkdir(parents=True, exist_ok=True)
        for name, dep in [("a", "missing/x"), ("b", "missing/y")]:
            (specdiff / "behaviors" / f"{name}.spec.md").write_text(
                f"---\nid: behaviors/{name}\nversion: '1.0.0'\nstatus: approved\n"
                f"depends_on:\n  - {dep}\n---\n\nSpec {name}.\n"
            )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "missing/x" in result.output
        assert "missing/y" in result.output
        assert "2 error(s)" in result.output


class TestHandEdits:
    def _build_then_edit(self, tmp_path):
        proj = _setup_project(
            tmp_path, [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}]
        )
        os.chdir(proj)
        with patch(LLM, FakeLLM()):
            result = CliRunner().invoke(cli, ["build"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        generated = proj / "src" / "auth_login.py"
        generated.write_text("# hotfix\n")
        spec = proj / ".specdiff" / "behaviors" / "auth" / "login.spec.md"
        spec.write_text(spec.read_text() + "\nMore detail.\n")
        return generated

    def test_status_lists_edited_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._build_then_edit(tmp_path)
        result = CliRunner().invoke(cli, ["status"], catch_exceptions=False)
        assert "edited by hand" in result.output
        assert "src/auth_login.py" in result.output

    def test_build_refuses_then_force_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        generated = self._build_then_edit(tmp_path)
        with patch(LLM, FakeLLM()):
            refused = CliRunner().invoke(cli, ["build"])
            assert refused.exit_code == 1
            assert generated.read_text() == "# hotfix\n"
            forced = CliRunner().invoke(cli, ["build", "--force"], catch_exceptions=False)
        assert forced.exit_code == 0, forced.output
        assert 'VALUE = "auth/login"' in generated.read_text()


class TestStalenessReporting:
    def test_init_project_builds_out_of_the_box(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        assert runner.invoke(cli, ["init"], catch_exceptions=False).exit_code == 0
        result = runner.invoke(cli, ["build", "--dry-run"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "behaviors/hello  [new]" in result.output

    def test_graph_error_is_a_clean_cli_error(self, tmp_path, monkeypatch):
        proj = _setup_project(
            tmp_path, [{"path": "a.spec.md", "id": "a", "depends_on": ["missing"]}]
        )
        monkeypatch.chdir(proj)
        result = CliRunner().invoke(cli, ["build"])
        assert result.exit_code == 1
        assert "a depends on missing" in result.output
        assert "Traceback" not in result.output

    def test_status_explains_downstream_staleness(self, tmp_path, monkeypatch):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "contracts/users.spec.md", "id": "contracts/users"},
                {
                    "path": "behaviors/login.spec.md",
                    "id": "behaviors/login",
                    "depends_on": ["contracts/users"],
                },
            ],
        )
        monkeypatch.chdir(proj)
        with patch(LLM, FakeLLM()):
            assert CliRunner().invoke(cli, ["build"], catch_exceptions=False).exit_code == 0

        contract = proj / ".specdiff" / "contracts" / "users.spec.md"
        contract.write_text(contract.read_text() + "\nNew field: email.\n")
        result = CliRunner().invoke(cli, ["status"], catch_exceptions=False)

        lines = {line.split()[0]: line for line in result.output.splitlines()[2:]}
        assert "spec changed" in lines["contracts/users"]
        assert "contracts/users changed" in lines["behaviors/login"]

    def test_skill_change_marks_everything_stale(self, tmp_path, monkeypatch):
        proj = _setup_project(tmp_path, [{"path": "a.spec.md", "id": "a"}])
        monkeypatch.chdir(proj)
        with patch(LLM, FakeLLM()):
            CliRunner().invoke(cli, ["build"], catch_exceptions=False)
        (proj / ".specdiff" / "skills" / "implement.skill.md").write_text("New rules")

        result = CliRunner().invoke(cli, ["status"], catch_exceptions=False)
        assert "skills changed" in result.output

    def test_build_skips_drafts_and_their_dependents(self, tmp_path, monkeypatch):
        proj = _setup_project(
            tmp_path,
            [
                {"path": "a.spec.md", "id": "a"},
                {"path": "b.spec.md", "id": "b", "depends_on": ["a"]},
                {"path": "c.spec.md", "id": "c"},
            ],
        )
        _write_spec(proj / ".specdiff", "a.spec.md", "a", status="draft")
        monkeypatch.chdir(proj)
        with patch(LLM, FakeLLM()) as llm:
            result = CliRunner().invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert [n for n, stage in llm.calls if stage == "plan"] == ["c"]
        assert "Skipping a (draft)" in result.output
        assert "Skipping b (waits on a)" in result.output


class TestSkillCommand:
    def test_prints_builtin_skill(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["skill", "repair"], catch_exceptions=False)
        assert "repair stage" in result.output

    def test_unknown_skill_errors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["skill", "nope"])
        assert result.exit_code == 1


class TestLegacySkillNotice:
    def test_build_notes_unused_legacy_skill_files(self, tmp_path, monkeypatch, fake_llm):
        proj = _setup_project(tmp_path, [{"path": "a.spec.md", "id": "a"}])
        (proj / ".specdiff" / "skills" / "architect.skill.md").write_text("old")
        monkeypatch.chdir(proj)
        result = CliRunner().invoke(cli, ["build"], catch_exceptions=False)
        assert "architect.skill.md is no longer used" in result.output


class TestValidateAcceptance:
    def test_missing_acceptance_file_is_reported(self, tmp_path, monkeypatch):
        proj = _setup_project(tmp_path, [])
        (proj / ".specdiff" / "a.spec.md").write_text(
            "---\nid: a\nversion: '1'\nstatus: approved\nacceptance:\n  - tests/acc.py\n---\nx\n"
        )
        monkeypatch.chdir(proj)
        result = CliRunner().invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "acceptance test 'tests/acc.py' not found" in result.output
