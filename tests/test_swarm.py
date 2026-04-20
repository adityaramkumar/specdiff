from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specdiff.agents.swarm import (
    REQUIRED_SKILLS,
    PipelineAgent,
    PipelineStep,
    _build_prompt,
    _run_pipeline_custom,
    build_pipeline,
    build_swarm,
    run_swarm,
)
from specdiff.llm import LLMResponse
from specdiff.types import SpecdiffConfig, SpecNode


def _make_node() -> SpecNode:
    return SpecNode(
        id="test/example",
        version="1.0.0",
        status="approved",
        hash="abc123",
        content="## Example\n\nReturn 200 on success.",
        file_path=".specdiff/test/example.spec.md",
    )


def _make_skills() -> dict[str, str]:
    return {name: f"Skill content for {name}" for name in REQUIRED_SKILLS}


def _setup_skills_dir(tmp_path: Path) -> Path:
    specs_dir = tmp_path / ".specdiff"
    skills_dir = specs_dir / "skills"
    skills_dir.mkdir(parents=True)
    for name in REQUIRED_SKILLS:
        (skills_dir / f"{name}.skill.md").write_text(f"Skill for {name}")
    return specs_dir


# ---------------------------------------------------------------------------
# ADK pipeline structure tests
# ---------------------------------------------------------------------------


class TestBuildSwarm:
    def test_structure(self):
        config = SpecdiffConfig()
        pipeline = build_swarm(config, _make_skills())

        assert pipeline.name == "build_pipeline"
        assert len(pipeline.sub_agents) == 5
        names = [a.name for a in pipeline.sub_agents]
        assert names == ["architect", "interface_planner", "implementation", "testing", "review"]

    def test_testing_follows_implementation(self):
        config = SpecdiffConfig()
        pipeline = build_swarm(config, _make_skills())
        names = [a.name for a in pipeline.sub_agents]
        assert names.index("testing") == names.index("implementation") + 1


# ---------------------------------------------------------------------------
# Custom pipeline structure tests
# ---------------------------------------------------------------------------


class TestBuildPipeline:
    def test_structure(self):
        steps = build_pipeline(_make_skills())

        assert len(steps) == 5

        assert steps[0].agents[0].name == "architect"
        assert steps[0].agents[0].output_key == "file_plan"

        assert steps[1].agents[0].name == "interface_planner"
        assert steps[1].agents[0].output_key == "interface_spec"

        assert steps[2].agents[0].name == "implementation"
        assert steps[2].agents[0].output_key == "generated_code"

        assert steps[3].agents[0].name == "testing"
        assert steps[3].agents[0].output_key == "generated_tests"

        assert steps[4].agents[0].name == "review"
        assert steps[4].agents[0].output_key == "review_result"

    def test_testing_follows_implementation(self):
        steps = build_pipeline(_make_skills())
        names = [s.agents[0].name for s in steps]
        assert names.index("testing") == names.index("implementation") + 1

    def test_all_steps_are_single_agent(self):
        steps = build_pipeline(_make_skills())
        for step in steps:
            assert len(step.agents) == 1


class TestRunPipelineCustom:
    @patch("specdiff.agents.swarm.generate_content")
    def test_sequential_steps(self, mock_gen):
        mock_gen.return_value = LLMResponse(text="agent output")
        steps = [
            PipelineStep(agents=[PipelineAgent("a1", "inst1", "out1")]),
            PipelineStep(agents=[PipelineAgent("a2", "inst2", "out2")]),
        ]
        outputs = _run_pipeline_custom(steps, "grok-4-1-fast-non-reasoning", "prompt")

        assert "out1" in outputs
        assert "out2" in outputs
        assert mock_gen.call_count == 2

    @patch("specdiff.agents.swarm.generate_content")
    def test_multi_agent_step_raises(self, mock_gen):
        mock_gen.return_value = LLMResponse(text="output")
        steps = [
            PipelineStep(
                agents=[
                    PipelineAgent("a1", "inst1", "out1"),
                    PipelineAgent("a2", "inst2", "out2"),
                ]
            ),
        ]
        with pytest.raises(RuntimeError, match="single-agent steps"):
            _run_pipeline_custom(steps, "some-model", "prompt")

    @patch("specdiff.agents.swarm.generate_content")
    def test_testing_receives_implementation_output_in_context(self, mock_gen):
        """Testing agent's context must include the generated_code from implementation."""
        call_contexts: dict[str, str] = {}

        def capture(model, contents, system_instruction):
            call_contexts[system_instruction] = contents
            return LLMResponse(text="output from " + system_instruction[:4])

        mock_gen.side_effect = capture
        skills = _make_skills()
        steps = build_pipeline(skills)
        _run_pipeline_custom(steps, "grok-model", "initial prompt")

        testing_context = call_contexts[skills["testing"]]
        assert "generated_code" in testing_context
        assert "output from " in testing_context


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


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
        assert "DEPENDENCY SPEC: contracts/api" in prompt
        assert "API Contract" in prompt


# ---------------------------------------------------------------------------
# Language resolution (uses default Gemini model -> ADK path)
# ---------------------------------------------------------------------------


class TestLanguageResolution:
    @patch("specdiff.agents.swarm._run_pipeline_adk")
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
            file_path=".specdiff/test/example.spec.md",
            language="typescript",
        )
        config = SpecdiffConfig(language="python", test_framework="pytest")
        run_swarm(node, config, specs_dir)

        call_args = mock_pipeline.call_args
        prompt = call_args[0][1]
        assert "Language: typescript" in prompt

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_config_language_used_when_no_spec_override(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        config = SpecdiffConfig(language="typescript", test_framework="vitest")
        run_swarm(_make_node(), config, specs_dir)

        call_args = mock_pipeline.call_args
        prompt = call_args[0][1]
        assert "Language: typescript" in prompt
        assert "Test Framework: vitest" in prompt


# ---------------------------------------------------------------------------
# run_swarm (ADK path — default model is gemini-*)
# ---------------------------------------------------------------------------


class TestRunSwarm:
    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_pass(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": json.dumps({"auth/login.ts": "Login handler"}),
            "generated_code": json.dumps({"auth/login.ts": "export function login() {}"}),
            "generated_tests": json.dumps({"auth/login.test.ts": "test('login', () => {})"}),
            "review_result": json.dumps({"passed": True, "feedback": "All criteria met."}),
        }

        result = run_swarm(_make_node(), SpecdiffConfig(), specs_dir)
        assert result.review_passed is True
        assert "auth/login.ts" in result.generated_files
        assert "auth/login.test.ts" in result.generated_tests
        assert "auth/login.ts" in result.file_plan.files

    @patch("specdiff.agents.swarm._run_pipeline_adk")
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

        result = run_swarm(_make_node(), SpecdiffConfig(), specs_dir)
        assert result.review_passed is False
        assert "401" in result.review_feedback

    def test_missing_skills(self, tmp_path):
        specs_dir = tmp_path / ".specdiff"
        specs_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="Missing required skill files"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_invalid_json_fails(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "not json",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="Architect agent returned invalid JSON"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_missing_review_output_fails(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
        }

        with pytest.raises(ValueError, match="Swarm did not return outputs for: review"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_review_feedback_list_is_normalized(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": False, "feedback": ["a", "b"]}),
        }

        result = run_swarm(_make_node(), SpecdiffConfig(), specs_dir)
        assert result.review_passed is False
        assert result.review_feedback == "a\nb"


# ---------------------------------------------------------------------------
# run_swarm (custom path — xAI model)
# ---------------------------------------------------------------------------


class TestRunSwarmCustom:
    @patch("specdiff.agents.swarm._run_pipeline_custom")
    def test_xai_model_uses_custom_pipeline(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": json.dumps({"main.py": "entry point"}),
            "generated_code": json.dumps({"main.py": "print('hello')"}),
            "generated_tests": json.dumps({"test_main.py": "def test(): pass"}),
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        config = SpecdiffConfig(model="grok-4-1-fast-non-reasoning")
        result = run_swarm(_make_node(), config, specs_dir)

        assert result.review_passed is True
        assert "main.py" in result.generated_files
        mock_pipeline.assert_called_once()


# ---------------------------------------------------------------------------
# _validate_string_map error paths
# ---------------------------------------------------------------------------


class TestValidateStringMap:
    def test_non_string_value_raises(self):
        from specdiff.agents.swarm import _validate_string_map

        with pytest.raises(ValueError, match="string-to-string"):
            _validate_string_map({"key": 123}, "TestAgent")

    def test_non_string_value_nested_dict_raises(self):
        from specdiff.agents.swarm import _validate_string_map

        with pytest.raises(ValueError, match="string-to-string"):
            _validate_string_map({"key": {"nested": "dict"}}, "TestAgent")

    def test_valid_string_map_passes(self):
        from specdiff.agents.swarm import _validate_string_map

        result = _validate_string_map({"a": "1", "b": "2"}, "TestAgent")
        assert result == {"a": "1", "b": "2"}

    def test_empty_map_passes(self):
        from specdiff.agents.swarm import _validate_string_map

        assert _validate_string_map({}, "TestAgent") == {}


# ---------------------------------------------------------------------------
# _normalize_review_feedback error paths
# ---------------------------------------------------------------------------


class TestNormalizeReviewFeedback:
    def test_string_passthrough(self):
        from specdiff.agents.swarm import _normalize_review_feedback

        assert _normalize_review_feedback("great work") == "great work"

    def test_list_of_strings_joined(self):
        from specdiff.agents.swarm import _normalize_review_feedback

        assert _normalize_review_feedback(["item a", "item b"]) == "item a\nitem b"

    def test_integer_raises(self):
        from specdiff.agents.swarm import _normalize_review_feedback

        with pytest.raises(ValueError, match="string 'feedback'"):
            _normalize_review_feedback(42)

    def test_dict_raises(self):
        from specdiff.agents.swarm import _normalize_review_feedback

        with pytest.raises(ValueError, match="string 'feedback'"):
            _normalize_review_feedback({"score": 1})

    def test_none_raises(self):
        from specdiff.agents.swarm import _normalize_review_feedback

        with pytest.raises(ValueError, match="string 'feedback'"):
            _normalize_review_feedback(None)


# ---------------------------------------------------------------------------
# _extract_json_object error paths
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    def test_non_dict_json_raises(self):
        from specdiff.agents.swarm import _extract_json_object

        with pytest.raises(ValueError, match="must return a JSON object"):
            _extract_json_object("[1, 2, 3]", "TestAgent")

    def test_invalid_json_raises(self):
        from specdiff.agents.swarm import _extract_json_object

        with pytest.raises(ValueError, match="invalid JSON"):
            _extract_json_object("not json", "TestAgent")

    def test_invalid_json_includes_response_preview(self):
        from specdiff.agents.swarm import _extract_json_object

        with pytest.raises(ValueError, match="Response preview"):
            _extract_json_object("Here is my response: blah blah", "TestAgent")

    def test_invalid_json_truncates_long_response(self):
        from specdiff.agents.swarm import _extract_json_object

        long_response = "x" * 500
        with pytest.raises(ValueError) as exc_info:
            _extract_json_object(long_response, "TestAgent")
        assert len(str(exc_info.value)) < 500

    def test_valid_dict_passes(self):
        from specdiff.agents.swarm import _extract_json_object

        result = _extract_json_object('{"key": "value"}', "TestAgent")
        assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# run_swarm: missing outputs and malformed review
# ---------------------------------------------------------------------------


class TestRunSwarmErrorPaths:
    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_missing_generated_code_fails(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="implementation"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_missing_generated_tests_fails(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="testing"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_review_passed_is_string_raises(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": "yes", "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="boolean 'passed'"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_review_passed_is_none_raises(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "{}",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": None, "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="boolean 'passed'"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)

    @patch("specdiff.agents.swarm._run_pipeline_adk")
    def test_generated_code_is_array_raises(self, mock_pipeline, tmp_path):
        specs_dir = _setup_skills_dir(tmp_path)
        mock_pipeline.return_value = {
            "file_plan": "{}",
            "generated_code": "[1, 2, 3]",
            "generated_tests": "{}",
            "review_result": json.dumps({"passed": True, "feedback": "ok"}),
        }

        with pytest.raises(ValueError, match="must return a JSON object"):
            run_swarm(_make_node(), SpecdiffConfig(), specs_dir)


# ---------------------------------------------------------------------------
# _build_prompt: dep_generated and prior_critique
# ---------------------------------------------------------------------------


class TestBuildPromptExtended:
    def test_dep_generated_appears_in_prompt(self):
        from specdiff.agents.swarm import _build_prompt

        prompt = _build_prompt(
            _make_node(),
            dep_generated={"src/api.py": "def get(): pass"},
            language="python",
        )
        assert "DEPENDENCY IMPLEMENTATION: src/api.py" in prompt
        assert "def get(): pass" in prompt

    def test_prior_critique_appears_in_prompt(self):
        from specdiff.agents.swarm import _build_prompt

        prompt = _build_prompt(_make_node(), prior_critique="Missing error handling.")
        assert "PREVIOUS REVIEW CRITIQUE" in prompt
        assert "Missing error handling." in prompt

    def test_no_critique_section_when_none(self):
        from specdiff.agents.swarm import _build_prompt

        prompt = _build_prompt(_make_node(), prior_critique=None)
        assert "PREVIOUS REVIEW CRITIQUE" not in prompt

    def test_dep_generated_none_omitted(self):
        from specdiff.agents.swarm import _build_prompt

        prompt = _build_prompt(_make_node(), dep_generated=None, language="python")
        assert "DEPENDENCY IMPLEMENTATION" not in prompt
