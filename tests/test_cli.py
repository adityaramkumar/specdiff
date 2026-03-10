from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specanopy.agents.swarm import REQUIRED_SKILLS
from specanopy.cli import cli
from specanopy.types import FilePlan, ReviewResult, SwarmResult


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
    """Create a minimal project with .specanopy/config.yaml, skill files, and spec files."""
    specanopy_dir = tmp_path / ".specanopy"
    specanopy_dir.mkdir()
    (specanopy_dir / "config.yaml").write_text(
        "model: gemini-3.1-flash-lite-preview\noutput_dir: src\nspecs_dir: .specanopy\n"
    )

    skills_dir = specanopy_dir / "skills"
    skills_dir.mkdir()
    for name in REQUIRED_SKILLS:
        (skills_dir / f"{name}.skill.md").write_text(f"Skill for {name}")
    if with_skill:
        (skills_dir / "spec-eval.skill.md").write_text("## Role\nYou review specs.\n")

    for s in specs:
        _write_spec(specanopy_dir, s["path"], s["id"], s.get("depends_on"))
    return tmp_path


def _mock_swarm_result(node, config, specs_dir, dep_specs=None):
    """Fake swarm that returns a SwarmResult writing one file per node."""
    return SwarmResult(
        file_plan=FilePlan(files={f"{node.id.replace('/', '_')}.py": "impl"}),
        generated_files={f"{node.id.replace('/', '_')}.py": f"# generated from {node.id}\n"},
        generated_tests={},
        review_passed=True,
        review_feedback="All criteria met.",
    )


def _mock_swarm_result_ts(node, config, specs_dir, dep_specs=None):
    return SwarmResult(
        file_plan=FilePlan(files={"auth/login.ts": "impl"}),
        generated_files={"auth/login.ts": "export function login() {}\n"},
        generated_tests={},
        review_passed=True,
        review_feedback="All criteria met.",
    )


def _mock_swarm_review_fail(node, config, specs_dir, dep_specs=None):
    return SwarmResult(
        file_plan=FilePlan(files={"auth/login.ts": "impl"}),
        generated_files={"auth/login.ts": "export function login() {}\n"},
        generated_tests={},
        review_passed=False,
        review_feedback="Spec mismatch.",
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


class TestBuild:
    @patch("specanopy.runner.run_swarm", side_effect=_mock_swarm_result)
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

        hm_path = proj / ".specanopy" / "hash-map.json"
        assert hm_path.exists()
        data = json.loads(hm_path.read_text())
        assert "auth/login" in data

    @patch("specanopy.runner.run_swarm", side_effect=_mock_swarm_result)
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

    @patch("specanopy.runner.run_swarm", side_effect=_mock_swarm_result_ts)
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

    @patch("specanopy.runner.run_swarm", side_effect=_mock_swarm_review_fail)
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
        hm_path = proj / ".specanopy" / "hash-map.json"
        data = json.loads(hm_path.read_text())
        assert "auth/login" not in data


class TestImpact:
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
        from specanopy.parser import parse_spec_file

        contract = parse_spec_file(proj / ".specanopy" / "contracts" / "schema.spec.md")
        hm_data = {
            contract.id: {
                "spec_hash": contract.hash,
                "generated_files": [],
                "generated_at": "",
            }
        }
        (proj / ".specanopy" / "hash-map.json").write_text(json.dumps(hm_data))

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
        from specanopy.parser import parse_spec_file

        node = parse_spec_file(proj / ".specanopy" / "behaviors" / "auth" / "login.spec.md")
        hm_data = {node.id: {"spec_hash": node.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specanopy" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "up to date" in result.output


def _mock_review_pass(node, skill, config):
    return ReviewResult(passed=True, feedback="All criteria met.")


def _mock_review_fail(node, skill, config):
    return ReviewResult(
        passed=False,
        feedback="Vague error handling.",
        proposed_revision="## Revised\n\nReturn HTTP 500.",
    )


class TestReview:
    @patch("specanopy.cli.review_spec", side_effect=_mock_review_pass)
    def test_review_pass(self, mock_review, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        _write_spec(
            proj / ".specanopy",
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

    @patch("specanopy.cli.review_spec", side_effect=_mock_review_fail)
    def test_review_fail_writes_proposal(self, mock_review, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        _write_spec(
            proj / ".specanopy",
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
        proposed = proj / ".specanopy" / "proposed" / "auth_login.spec.md"
        assert proposed.exists()

    @patch("specanopy.runner.run_swarm", side_effect=_mock_swarm_result)
    @patch("specanopy.cli.review_spec", side_effect=_mock_review_pass)
    def test_build_reviews_all_stale_specs_when_enabled(self, mock_review, mock_swarm, tmp_path):
        proj = _setup_project(
            tmp_path,
            [{"path": "behaviors/login.spec.md", "id": "auth/login"}],
            with_skill=True,
        )
        (proj / ".specanopy" / "config.yaml").write_text(
            "model: gemini-3.1-flash-lite-preview\n"
            "output_dir: src\n"
            "specs_dir: .specanopy\n"
            "review_before_build: true\n"
        )
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        mock_review.assert_called_once()
