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

    file_plan_raw = outputs.get("file_plan", "{}")
    generated_code_raw = outputs.get("generated_code", "{}")
    generated_tests_raw = outputs.get("generated_tests", "{}")
    review_raw = outputs.get("review_result", '{"passed": true, "feedback": ""}')

    try:
        file_plan_data = extract_json(file_plan_raw)
    except Exception:
        file_plan_data = {}

    try:
        generated_files = extract_json(generated_code_raw)
    except Exception:
        generated_files = {}

    try:
        generated_tests = extract_json(generated_tests_raw)
    except Exception:
        generated_tests = {}

    try:
        review_data = extract_json(review_raw)
    except Exception:
        review_data = {"passed": True, "feedback": ""}

    return SwarmResult(
        file_plan=FilePlan(files=file_plan_data),
        generated_files=generated_files,
        generated_tests=generated_tests,
        review_passed=bool(review_data.get("passed", True)),
        review_feedback=review_data.get("feedback", ""),
    )
