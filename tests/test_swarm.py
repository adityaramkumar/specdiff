from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specanopy.agents.swarm import REQUIRED_SKILLS, _build_prompt, build_swarm, run_swarm
from specanopy.types import SpecanopyConfig, SpecNode


def _make_node() -> SpecNode:
    return SpecNode(
        id="test/example",
        version="1.0.0",
        status="approved",
        hash="abc123",
        content="## Example\n\nReturn 200 on success.",
        file_path=".specanopy/test/example.spec.md",
    )


def _make_skills() -> dict[str, str]:
    return {name: f"Skill content for {name}" for name in REQUIRED_SKILLS}


def _setup_skills_dir(tmp_path: Path) -> Path:
    specs_dir = tmp_path / ".specanopy"
    skills_dir = specs_dir / "skills"
    skills_dir.mkdir(parents=True)
    for name in REQUIRED_SKILLS:
        (skills_dir / f"{name}.skill.md").write_text(f"Skill for {name}")
    return specs_dir


class TestBuildSwarm:
    def test_structure(self):
        config = SpecanopyConfig()
        pipeline = build_swarm(config, _make_skills())

        assert pipeline.name == "build_pipeline"
        assert len(pipeline.sub_agents) == 4
        assert pipeline.sub_agents[0].name == "architect"
        assert pipeline.sub_agents[1].name == "interface_planner"
        assert pipeline.sub_agents[2].name == "generators"
        assert pipeline.sub_agents[3].name == "review"

        parallel = pipeline.sub_agents[2]
        assert len(parallel.sub_agents) == 2
        sub_names = {a.name for a in parallel.sub_agents}
        assert sub_names == {"implementation", "testing"}


class TestBuildPrompt:
    def test_includes_language(self):
        prompt = _build_prompt(_make_node(), language="typescript")
        assert "Language: typescript" in prompt

    def test_includes_test_framework(self):
        prompt = _build_prompt(_make_node(), language="python", test_framework="pytest")
        assert "Language: python" in prompt
        assert "Test Framework: pytest" in prompt

    def test_omits_test_framework_when_none(self):
        prompt = _build_prompt(_make_node(), language="python", test_framework=None)
        assert "Test Framework:" not in prompt

    def test_default_language_is_python(self):
        prompt = _build_prompt(_make_node())
        assert "Language: python" in prompt

    def test_includes_dependency_context(self):
        dep = SpecNode(
            id="contracts/api",
            version="1.0.0",
            status="approved",
            hash="def456",
            content="## API Contract",
            file_path="contracts/api.spec.md",
        )
        prompt = _build_prompt(_make_node(), [dep], language="typescript")
        assert "DEPENDENCY: contracts/api" in prompt
        assert "API Contract" in prompt


class TestLanguageResolution:
    @patch("specanopy.agents.swarm._run_pipeline")
    def test_spec_language_overrides_config(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        node = SpecNode(
            id="test/example",
            version="1.0.0",
            status="approved",
            hash="abc123",
            content="## Example",
            file_path=".specanopy/test/example.spec.md",
            language="typescript",
        )
        config = SpecanopyConfig(language="python", test_framework="pytest")
        run_swarm(node, config, specs_dir)

        call_args = mock_pipeline.call_args
        prompt = call_args[0][1]
        assert "Language: typescript" in prompt

    @patch("specanopy.agents.swarm._run_pipeline")
    def test_config_language_used_when_no_spec_override(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        config = SpecanopyConfig(language="typescript", test_framework="vitest")
        run_swarm(_make_node(), config, specs_dir)

        call_args = mock_pipeline.call_args
        prompt = call_args[0][1]
        assert "Language: typescript" in prompt
        assert "Test Framework: vitest" in prompt


class TestRunSwarm:
    @patch("specanopy.agents.swarm._run_pipeline")
    def test_pass(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": json.dumps({"auth/login.ts": "Login handler"}),
            "generated_code": json.dumps({"auth/login.ts": "export function login() {}"}),
            "generated_tests": json.dumps({"auth/login.test.ts": "test('login', () => {})"}),
            "review_result": json.dumps({"passed": True, "feedback": "All criteria met."}),
        }

        result = run_swarm(_make_node(), SpecanopyConfig(), specs_dir)
        assert result.review_passed is True
        assert "auth/login.ts" in result.generated_files
        assert "auth/login.test.ts" in result.generated_tests
        assert "auth/login.ts" in result.file_plan.files

    @patch("specanopy.agents.swarm._run_pipeline")
    def test_review_fail(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps(
                {
                    "passed": False,
                    "feedback": "Missing error handling for 401.",
                }
            ),
        }

        result = run_swarm(_make_node(), SpecanopyConfig(), specs_dir)
        assert result.review_passed is False
        assert "401" in result.review_feedback

    def test_missing_skills(self, tmp_path):
        specs_dir = tmp_path / ".specanopy"
        specs_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="Missing required skill files"):
            run_swarm(_make_node(), SpecanopyConfig(), specs_dir)

    @patch("specanopy.agents.swarm._run_pipeline")
    def test_invalid_json_fails(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "not json",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="Architect agent returned invalid JSON"):
            run_swarm(_make_node(), SpecanopyConfig(), specs_dir)

    @patch("specanopy.agents.swarm._run_pipeline")
    def test_missing_review_output_fails(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
        }

        with pytest.raises(ValueError, match="Swarm did not return outputs for: review"):
            run_swarm(_make_node(), SpecanopyConfig(), specs_dir)

    @patch("specanopy.agents.swarm._run_pipeline")
    def test_review_feedback_list_is_normalized(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": False, "feedback": ["a", "b"]}),
        }

        result = run_swarm(_make_node(), SpecanopyConfig(), specs_dir)
        assert result.review_passed is False
        assert result.review_feedback == "a\nb"
