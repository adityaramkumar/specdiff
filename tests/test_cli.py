from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specanopy.cli import cli


def _write_spec(root: Path, rel_path: str, spec_id: str, depends_on: list[str] | None = None) -> None:
    dep_line = ""
    if depends_on:
        items = "\n".join(f"  - {d}" for d in depends_on)
        dep_line = f"depends_on:\n{items}\n"
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {spec_id}\nversion: '1.0.0'\nstatus: approved\n{dep_line}---\n\nSpec body for {spec_id}\n"
    )


def _setup_project(tmp_path: Path, specs: list[dict]) -> Path:
    """Create a minimal project with .specanopy/config.yaml and spec files."""
    specanopy_dir = tmp_path / ".specanopy"
    specanopy_dir.mkdir()
    (specanopy_dir / "config.yaml").write_text(
        "model: gemini-3.1-flash-lite-preview\noutput_dir: src\nspecs_dir: .specanopy\n"
    )
    for s in specs:
        _write_spec(specanopy_dir, s["path"], s["id"], s.get("depends_on"))
    return tmp_path


def _mock_generate(node, config, dep_specs=None):
    """Fake generator that writes a single file per node."""
    out = Path(config.output_dir) / f"{node.id.replace('/', '_')}.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"# generated from {node.id}\n")
    return [str(out)]


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
        proj = _setup_project(tmp_path, [
            {"path": "behaviors/auth/login.spec.md", "id": "auth/login"},
        ])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["status"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "auth/login" in result.output
        assert "new" in result.output


class TestBuild:
    @patch("specanopy.runner.generate", side_effect=_mock_generate)
    def test_updates_hashmap(self, mock_gen, tmp_path):
        proj = _setup_project(tmp_path, [
            {"path": "behaviors/auth/login.spec.md", "id": "auth/login"},
        ])
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

    @patch("specanopy.runner.generate", side_effect=_mock_generate)
    def test_idempotent(self, mock_gen, tmp_path):
        proj = _setup_project(tmp_path, [
            {"path": "behaviors/auth/login.spec.md", "id": "auth/login"},
        ])
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            runner.invoke(cli, ["build"], catch_exceptions=False)
            result = runner.invoke(cli, ["build"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "Everything is up to date" in result.output


class TestImpact:
    def test_shows_cascade(self, tmp_path):
        proj = _setup_project(tmp_path, [
            {"path": "contracts/schema.spec.md", "id": "contracts/schema"},
            {"path": "behaviors/auth/login.spec.md", "id": "auth/login", "depends_on": ["contracts/schema"]},
        ])
        # Mark the contract as current so only login is stale directly,
        # making login appear as downstream of the contract change test.
        from specanopy.parser import parse_spec_file
        contract = parse_spec_file(proj / ".specanopy" / "contracts" / "schema.spec.md")
        hm_data = {contract.id: {"spec_hash": contract.hash, "generated_files": [], "generated_at": ""}}
        (proj / ".specanopy" / "hash-map.json").write_text(json.dumps(hm_data))

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(proj)
            result = runner.invoke(cli, ["impact"], catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert "auth/login" in result.output
        assert "node(s) will be rebuilt" in result.output

    def test_up_to_date(self, tmp_path):
        proj = _setup_project(tmp_path, [
            {"path": "behaviors/auth/login.spec.md", "id": "auth/login"},
        ])
        # Pre-populate hashmap so node is current
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
