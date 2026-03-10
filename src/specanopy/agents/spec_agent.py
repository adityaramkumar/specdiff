from __future__ import annotations

from specanopy.llm import extract_json, get_gemini_client
from specanopy.types import ReviewResult, SpecanopyConfig, SpecNode

REVIEW_PROMPT_TEMPLATE = """\
Review the following spec. Evaluate it against the criteria in your system prompt.

Spec ID: {node_id}
Version: {version}

--- SPEC CONTENT ---
{content}
--- END SPEC ---

Reply with ONLY a JSON object with these fields:
- "passed": true if the spec meets all criteria, false otherwise
- "feedback": a string with bullet points explaining your evaluation
- "proposed_revision": if the spec failed, provide a complete rewritten spec body \
that fixes all issues. If it passed, set this to null.

Return raw JSON only, no markdown fences.
"""


def review_spec(node: SpecNode, skill_content: str, config: SpecanopyConfig) -> ReviewResult:
    """Run the Spec Agent to evaluate a spec node against a skill's criteria."""
    client = get_gemini_client()

    prompt = REVIEW_PROMPT_TEMPLATE.format(
        node_id=node.id,
        version=node.version,
        content=node.content,
    )

    response = client.models.generate_content(
        model=config.model,
        config={"system_instruction": skill_content},
        contents=prompt,
    )

    data = extract_json(response.text)
    return ReviewResult(
        passed=bool(data.get("passed", False)),
        feedback=data.get("feedback", ""),
        proposed_revision=data.get("proposed_revision"),
    )
