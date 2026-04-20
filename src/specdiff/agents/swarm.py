from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from specdiff.llm import detect_provider, extract_json, generate_content
from specdiff.skills import discover_skills
from specdiff.types import FilePlan, SpecdiffConfig, SpecNode, SwarmResult

REQUIRED_SKILLS = ("architect", "interface", "implementation", "testing", "review")


# ---------------------------------------------------------------------------
# ADK pipeline (used for Gemini models)
# ---------------------------------------------------------------------------


def build_swarm(config: SpecdiffConfig, skill_content: dict[str, str]) -> SequentialAgent:
    """Build the multi-agent pipeline from skill files (ADK path)."""
    architect = LlmAgent(
        name="architect",
        model=config.model,
        instruction=skill_content["architect"],
        output_key="file_plan",
    )
    interface_planner = LlmAgent(
        name="interface_planner",
        model=config.model,
        instruction=skill_content["interface"],
        output_key="interface_spec",
    )
    implementation = LlmAgent(
        name="implementation",
        model=config.model,
        instruction=skill_content["implementation"],
        output_key="generated_code",
    )
    testing = LlmAgent(
        name="testing",
        model=config.model,
        instruction=skill_content["testing"],
        output_key="generated_tests",
    )
    review = LlmAgent(
        name="review",
        model=config.model,
        instruction=skill_content["review"],
        output_key="review_result",
    )

    parallel = ParallelAgent(
        name="generators",
        sub_agents=[implementation, testing],
    )

    return SequentialAgent(
        name="build_pipeline",
        sub_agents=[architect, interface_planner, parallel, review],
    )


async def _run_pipeline_adk(pipeline: SequentialAgent, prompt: str) -> dict[str, str]:
    """Run the ADK pipeline and collect output_key values from session state."""
    runner = InMemoryRunner(agent=pipeline, app_name="specdiff")
    session = await runner.session_service.create_session(app_name="specdiff", user_id="specdiff")

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

    outputs: dict[str, str] = {}
    async for event in runner.run_async(
        new_message=content,
        user_id="specdiff",
        session_id=session.id,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = "".join(p.text for p in event.content.parts if getattr(p, "text", None))
            if text:
                outputs["final"] = text

    updated_session = await runner.session_service.get_session(
        app_name="specdiff",
        user_id="specdiff",
        session_id=session.id,
    )
    if updated_session and updated_session.state:
        outputs.update(updated_session.state)

    return outputs


# ---------------------------------------------------------------------------
# Custom pipeline (used for non-Gemini models: xAI, OpenAI, etc.)
# ---------------------------------------------------------------------------


@dataclass
class PipelineAgent:
    name: str
    instruction: str
    output_key: str


@dataclass
class PipelineStep:
    agents: list[PipelineAgent]


def build_pipeline(skill_content: dict[str, str]) -> list[PipelineStep]:
    """Build the multi-agent pipeline from skill files (custom path)."""
    return [
        PipelineStep(
            agents=[
                PipelineAgent("architect", skill_content["architect"], "file_plan"),
            ]
        ),
        PipelineStep(
            agents=[
                PipelineAgent("interface_planner", skill_content["interface"], "interface_spec"),
            ]
        ),
        PipelineStep(
            agents=[
                PipelineAgent("implementation", skill_content["implementation"], "generated_code"),
                PipelineAgent("testing", skill_content["testing"], "generated_tests"),
            ]
        ),
        PipelineStep(
            agents=[
                PipelineAgent("review", skill_content["review"], "review_result"),
            ]
        ),
    ]


def _run_pipeline_custom(steps: list[PipelineStep], model: str, prompt: str) -> dict[str, str]:
    """Run the custom pipeline using generate_content() for each agent."""
    outputs: dict[str, str] = {}
    context = prompt

    for step in steps:
        if len(step.agents) == 1:
            agent = step.agents[0]
            resp = generate_content(
                model=model,
                contents=context,
                system_instruction=agent.instruction,
            )
            outputs[agent.output_key] = resp.text
            context += f"\n\n--- {agent.output_key} ---\n{resp.text}"
        else:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future_map = {
                    pool.submit(
                        generate_content,
                        model=model,
                        contents=context,
                        system_instruction=a.instruction,
                    ): a
                    for a in step.agents
                }
                for future in concurrent.futures.as_completed(future_map):
                    agent = future_map[future]
                    text = future.result().text
                    outputs[agent.output_key] = text
                    context += f"\n\n--- {agent.output_key} ---\n{text}"

    return outputs


# ---------------------------------------------------------------------------
# Shared helpers and orchestration
# ---------------------------------------------------------------------------


def _build_prompt(
    node: SpecNode,
    dep_specs: list[SpecNode] | None = None,
    dep_generated: dict[str, str] | None = None,
    *,
    language: str = "python",
    test_framework: str | None = None,
    prior_critique: str | None = None,
) -> str:
    dep_context = ""
    for dep in dep_specs or []:
        dep_context += (
            f"\n--- DEPENDENCY SPEC: {dep.id} ---\n{dep.content}\n--- END DEPENDENCY SPEC ---\n"
        )
    for file_path, content in (dep_generated or {}).items():
        dep_context += (
            f"\n--- DEPENDENCY IMPLEMENTATION: {file_path} ---\n"
            f"{content}\n--- END DEPENDENCY IMPLEMENTATION ---\n"
        )

    framework_line = f"Test Framework: {test_framework}\n" if test_framework else ""

    critique_section = ""
    if prior_critique:
        critique_section = (
            f"\n--- PREVIOUS REVIEW CRITIQUE ---\n"
            f"{prior_critique}\n"
            f"Fix every issue listed above in your revised output.\n"
            f"--- END CRITIQUE ---\n"
        )

    return (
        f"Spec ID: {node.id}\n"
        f"Version: {node.version}\n"
        f"Language: {language}\n"
        f"{framework_line}\n"
        f"--- SPEC CONTENT ---\n{node.content}\n--- END SPEC ---\n"
        f"{dep_context}"
        f"{critique_section}"
    )


def _extract_json_object(raw_output: str, label: str) -> dict:
    try:
        data = extract_json(raw_output)
    except Exception as exc:
        raise ValueError(f"{label} agent returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{label} agent must return a JSON object.")
    return data


def _validate_string_map(data: dict, label: str) -> dict[str, str]:
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise ValueError(f"{label} agent must return a string-to-string JSON object.")
    return data


def _normalize_review_feedback(feedback: object) -> str:
    if isinstance(feedback, str):
        return feedback
    if isinstance(feedback, list) and all(isinstance(item, str) for item in feedback):
        return "\n".join(feedback)
    raise ValueError("Review agent must return a string 'feedback' field.")


def run_swarm(
    node: SpecNode,
    config: SpecdiffConfig,
    specs_dir: Path,
    dep_specs: list[SpecNode] | None = None,
    dep_generated: dict[str, str] | None = None,
    prior_critique: str | None = None,
) -> SwarmResult:
    """Run one attempt of the multi-agent swarm for a single spec node."""
    skills = discover_skills(specs_dir)
    missing = [s for s in REQUIRED_SKILLS if s not in skills]
    if missing:
        raise FileNotFoundError(
            f"Missing required skill files: {', '.join(missing)}\n"
            f"Create them in {specs_dir / 'skills'}/"
        )

    language = node.language or config.language
    prompt = _build_prompt(
        node,
        dep_specs,
        dep_generated,
        language=language,
        test_framework=config.test_framework,
        prior_critique=prior_critique,
    )

    provider_name, _ = detect_provider(config.model)
    if provider_name == "gemini":
        pipeline = build_swarm(config, skills)
        outputs = asyncio.run(_run_pipeline_adk(pipeline, prompt))
    else:
        steps = build_pipeline(skills)
        outputs = _run_pipeline_custom(steps, config.model, prompt)

    required_outputs = {
        "file_plan": "architect",
        "generated_code": "implementation",
        "generated_tests": "testing",
        "review_result": "review",
    }
    missing_outputs = [key for key in required_outputs if key not in outputs]
    if missing_outputs:
        missing_agents = ", ".join(required_outputs[key] for key in missing_outputs)
        raise ValueError(f"Swarm did not return outputs for: {missing_agents}.")

    file_plan_data = _validate_string_map(
        _extract_json_object(outputs["file_plan"], "Architect"),
        "Architect",
    )
    generated_files = _validate_string_map(
        _extract_json_object(outputs["generated_code"], "Implementation"),
        "Implementation",
    )
    generated_tests = _validate_string_map(
        _extract_json_object(outputs["generated_tests"], "Testing"),
        "Testing",
    )
    review_data = _extract_json_object(outputs["review_result"], "Review")
    if not isinstance(review_data.get("passed"), bool):
        raise ValueError("Review agent must return a boolean 'passed' field.")

    return SwarmResult(
        file_plan=FilePlan(files=file_plan_data),
        generated_files=generated_files,
        generated_tests=generated_tests,
        review_passed=bool(review_data.get("passed", True)),
        review_feedback=_normalize_review_feedback(review_data.get("feedback", "")),
    )
