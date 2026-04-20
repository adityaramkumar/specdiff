from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specdiff.agents.swarm import REQUIRED_SKILLS
from specdiff.cli import cli
from specdiff.types import FilePlan, ReviewResult, SwarmResult


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
    for name in REQUIRED_SKILLS:
        (skills_dir / f"{name}.skill.md").write_text(f"Skill for {name}")
    if with_skill:
        (skills_dir / "spec-eval.skill.md").write_text("## Role\nYou review specs.\n")

    for s in specs:
        _write_spec(specdiff_dir, s["path"], s["id"], s.get("depends_on"))
    return tmp_path


def _mock_swarm_result(node, config, specs_dir, **kwargs):
    """Fake swarm that returns a SwarmResult writing one file per node."""
    return SwarmResult(
        file_plan=FilePlan(files={f"{node.id.replace('/', '_')}.py": "impl"}),
        generated_files={f"{node.id.replace('/', '_')}.py": f"# generated from {node.id}\n"},
        generated_tests={},
        review_passed=True,
        review_feedback="All criteria met.",
    )


def _mock_swarm_result_ts(node, config, specs_dir, **kwargs):
    return SwarmResult(
        file_plan=FilePlan(files={"auth/login.ts": "impl"}),
        generated_files={"auth/login.ts": "export function login() {}\n"},
        generated_tests={},
        review_passed=True,
        review_feedback="All criteria met.",
    )


def _mock_swarm_result_with_tests(node, config, specs_dir, **kwargs):
    return SwarmResult(
        file_plan=FilePlan(files={"auth/login.ts": "impl", "tests/auth/login.test.ts": "test"}),
        generated_files={"auth/login.ts": "export function login() {}\n"},
        generated_tests={"tests/auth/login.test.ts": "test('login', () => {})\n"},
        review_passed=True,
        review_feedback="All criteria met.",
    )


def _mock_swarm_review_fail(node, config, specs_dir, **kwargs):
    return SwarmResult(
        file_plan=FilePlan(files={"auth/login.ts": "impl"}),
        generated_files={"auth/login.ts": "export function login() {}\n"},
        generated_tests={},
        review_passed=False,
        review_feedback="Spec mismatch.",
    )


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

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_result)
    def test_build_single_node_id(self, mock_swarm, tmp_path):
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
        assert mock_swarm.call_count == 1

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_review_fail)
    def test_build_no_review_flag_continues_on_review_fail(self, mock_swarm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build", "--no-review"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "--no-review" in result.output

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

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_result)
    def test_updates_hashmap(self, mock_swarm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "Build complete" in result.output

        hm_path = proj / ".specdiff" / "hash-map.json"
        assert hm_path.exists()
        data = json.loads(hm_path.read_text())
        assert "auth/login" in data

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_result)
    def test_idempotent(self, mock_swarm, tmp_path):
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

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_result_ts)
    def test_writes_language_aware_traceability_headers(self, mock_swarm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        generated = proj / "src" / "auth" / "login.ts"
        assert generated.exists()
        assert generated.read_text().startswith("// generated_from: auth/login")

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_review_fail)
    def test_fails_build_when_swarm_review_fails(self, mock_swarm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"])

        assert result.exit_code == 1
        assert "review failed" in result.output
        hm_path = proj / ".specdiff" / "hash-map.json"
        if hm_path.exists():
            data = json.loads(hm_path.read_text())
            assert "auth/login" not in data

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_result_with_tests)
    def test_fails_build_when_generated_tests_have_no_test_command(self, mock_swarm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/auth/login.spec.md", "id": "auth/login"}],
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"])

        assert result.exit_code == 1
        assert "generated tests but no test_command is configured" in result.output
        hm_path = proj / ".specdiff" / "hash-map.json"
        if hm_path.exists():
            data = json.loads(hm_path.read_text())
            assert "auth/login" not in data


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

    def test_impact_node_not_stale(self, tmp_path):
        """When the targeted node is not stale, impact reports no changes needed."""
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
        assert "up to date" in result.output or "not stale" in result.output

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

    @patch("specdiff.runner.run_swarm", side_effect=_mock_swarm_result)
    @patch("specdiff.cli.review_spec", side_effect=_mock_review_pass)
    def test_build_reviews_all_stale_specs_when_enabled(self, mock_review, mock_swarm, tmp_path):
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
        assert (tmp_path / ".specdiff" / "skills").is_dir()
        assert (tmp_path / ".specdiff" / "skills" / "spec-eval.skill.md").exists()

    def test_init_message(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["init"], catch_exceptions=False)
        assert "Initialized" in result.output

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
