from __future__ import annotations

import asyncio
from pathlib import Path

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from specanopy.llm import extract_json
from specanopy.skills import discover_skills
from specanopy.types import FilePlan, SpecanopyConfig, SpecNode, SwarmResult

REQUIRED_SKILLS = ("architect", "implementation", "testing", "review")


def build_swarm(config: SpecanopyConfig, skill_content: dict[str, str]) -> SequentialAgent:
    """Build the multi-agent pipeline from skill files."""
    architect = LlmAgent(
        name="architect",
        model=config.model,
        instruction=skill_content["architect"],
        output_key="file_plan",
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
        sub_agents=[architect, parallel, review],
    )


def _build_prompt(node: SpecNode, dep_specs: list[SpecNode] | None = None) -> str:
    dep_context = ""
    for dep in dep_specs or []:
        dep_context += f"\n--- DEPENDENCY: {dep.id} ---\n{dep.content}\n--- END DEPENDENCY ---\n"

    return (
        f"Spec ID: {node.id}\n"
        f"Version: {node.version}\n\n"
        f"--- SPEC CONTENT ---\n{node.content}\n--- END SPEC ---\n"
        f"{dep_context}"
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


async def _run_pipeline(pipeline: SequentialAgent, prompt: str) -> dict[str, str]:
    """Run the ADK pipeline and collect output_key values from session state."""
    runner = InMemoryRunner(agent=pipeline, app_name="specanopy")
    session = await runner.session_service.create_session(app_name="specanopy", user_id="specanopy")

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

    outputs: dict[str, str] = {}
    async for event in runner.run_async(
        new_message=content,
        user_id="specanopy",
        session_id=session.id,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = "".join(p.text for p in event.content.parts if getattr(p, "text", None))
            if text:
                outputs["final"] = text

    updated_session = await runner.session_service.get_session(
        app_name="specanopy",
        user_id="specanopy",
        session_id=session.id,
    )
    if updated_session and updated_session.state:
        outputs.update(updated_session.state)

    return outputs


def run_swarm(
    node: SpecNode,
    config: SpecanopyConfig,
    specs_dir: Path,
    dep_specs: list[SpecNode] | None = None,
) -> SwarmResult:
    """Run the full multi-agent swarm for a single spec node."""
    skills = discover_skills(specs_dir)
    missing = [s for s in REQUIRED_SKILLS if s not in skills]
    if missing:
        raise FileNotFoundError(
            f"Missing required skill files: {', '.join(missing)}\n"
            f"Create them in {specs_dir / 'skills'}/"
        )

    pipeline = build_swarm(config, skills)
    prompt = _build_prompt(node, dep_specs)
    outputs = asyncio.run(_run_pipeline(pipeline, prompt))

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
    if not isinstance(review_data.get("feedback", ""), str):
        raise ValueError("Review agent must return a string 'feedback' field.")

    return SwarmResult(
        file_plan=FilePlan(files=file_plan_data),
        generated_files=generated_files,
        generated_tests=generated_tests,
        review_passed=bool(review_data.get("passed", True)),
        review_feedback=review_data.get("feedback", ""),
    )
