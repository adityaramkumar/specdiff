from __future__ import annotations

import re
from dataclasses import dataclass, field

from specdiff.agents import fileblocks
from specdiff.agents.context import NodeContext, render
from specdiff.llm import extract_json
from specdiff.providers import LLMResponse, complete


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, response: LLMResponse) -> None:
        self.calls += 1
        self.input_tokens += response.input_tokens
        self.output_tokens += response.output_tokens

    def __iadd__(self, other: Usage) -> Usage:
        self.calls += other.calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        return self


@dataclass
class Plan:
    code: dict[str, str] = field(default_factory=dict)
    tests: dict[str, str] = field(default_factory=dict)
    interface: str = ""

    def render(self) -> str:
        lines = ["# Plan", "", "Production files:"]
        lines += [f"- {p}: {why}" for p, why in self.code.items()]
        lines += ["", "Test files:"]
        lines += [f"- {p}: {why}" for p, why in self.tests.items()] or ["- (none)"]
        lines += ["", "Public interface:", "", self.interface.strip()]
        return "\n".join(lines)


class StageError(Exception):
    """An agent's reply could not be used."""


def _ask(model: str, system: str, prompt: str, usage: Usage) -> str:
    response = complete(model, prompt, system)
    usage.add(response)
    return response.text


_PLAN_CODE = re.compile(r'<code path="([^"]+)">(.*?)</code>', re.DOTALL)
_PLAN_TEST = re.compile(r'<test path="([^"]+)">(.*?)</test>', re.DOTALL)
_INTERFACE = re.compile(r"<interface>\n?(.*?)</interface>", re.DOTALL)

PLAN_TASK = """
# Your task: plan

Plan the files for spec `{id}`. Reply with one line per production file and per
test file, then the full public interface:

<code path="relative/path.ext">one-line purpose</code>
<test path="relative/path.ext">what it covers</test>
<interface>
signatures, types, return shapes, and exact error types and messages
</interface>
"""


def plan(ctx: NodeContext, system: str, model: str, usage: Usage) -> Plan:
    reply = _ask(model, system, render(ctx) + PLAN_TASK.format(id=ctx.node.id), usage)
    result = Plan(
        code={p.strip(): why.strip() for p, why in _PLAN_CODE.findall(reply)},
        tests={p.strip(): why.strip() for p, why in _PLAN_TEST.findall(reply)},
        interface=m.group(1) if (m := _INTERFACE.search(reply)) else "",
    )
    if not result.code:
        raise StageError(f"Plan for {ctx.node.id} listed no production files:\n{reply[:500]}")
    return result


IMPLEMENT_TASK = """
{plan}

# Your task: implement

Write every production file in the plan. {format}"""

TEST_TASK = """
{plan}

# Your task: test

Write every test file in the plan. {format}"""


def _write_files(task: str, ctx: NodeContext, p: Plan, system: str, model: str, usage: Usage):
    prompt = render(ctx) + task.format(plan=p.render(), format=fileblocks.FORMAT_INSTRUCTIONS)
    return fileblocks.parse(_ask(model, system, prompt, usage))


def implement(ctx: NodeContext, p: Plan, system: str, model: str, usage: Usage):
    return _write_files(IMPLEMENT_TASK, ctx, p, system, model, usage)


def write_tests(ctx: NodeContext, p: Plan, system: str, model: str, usage: Usage):
    return _write_files(TEST_TASK, ctx, p, system, model, usage)


REPAIR_TASK = """
{plan}

# Current files

{files}

# What failed

{failure}

# Your task: repair

Fix the cause of the failure. Return only the files you change, each in full,
and <delete path="relative/path.ext"/> for any file that should not exist.
{format}"""


def repair(
    ctx: NodeContext,
    p: Plan,
    files: dict[str, str],
    failure: str,
    system: str,
    model: str,
    usage: Usage,
) -> fileblocks.FileBlocks:
    prompt = render(ctx) + REPAIR_TASK.format(
        plan=p.render(),
        files=fileblocks.render(files),
        failure=failure,
        format=fileblocks.FORMAT_INSTRUCTIONS,
    )
    return fileblocks.parse(_ask(model, system, prompt, usage))


_VERDICT = re.compile(r"<verdict>\s*(pass|fail)\s*</verdict>", re.IGNORECASE)
_FEEDBACK = re.compile(r"<feedback>\n?(.*?)</feedback>", re.DOTALL)

REVIEW_TASK = """
{plan}

# Files

{files}

# Your task: review

Reply with <verdict>pass</verdict> or <verdict>fail</verdict>, then
<feedback>
your findings; for a fail, each problem and the specific fix
</feedback>
"""


def review(
    ctx: NodeContext, p: Plan, files: dict[str, str], system: str, model: str, usage: Usage
) -> tuple[bool, str]:
    prompt = render(ctx) + REVIEW_TASK.format(plan=p.render(), files=fileblocks.render(files))
    reply = _ask(model, system, prompt, usage)
    verdict = _VERDICT.search(reply)
    if verdict is None:
        return _legacy_review(ctx, reply)
    feedback = m.group(1).strip() if (m := _FEEDBACK.search(reply)) else reply.strip()
    return verdict.group(1).lower() == "pass", feedback


def _legacy_review(ctx: NodeContext, reply: str) -> tuple[bool, str]:
    """Review skills written for the previous pipeline ask for {"passed", "feedback"} JSON."""
    try:
        data = extract_json(reply)
    except ValueError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("passed"), bool):
        raise StageError(f"Review for {ctx.node.id} gave no verdict:\n{reply[:500]}")
    feedback = data.get("feedback", "")
    return data["passed"], "\n".join(feedback) if isinstance(feedback, list) else str(feedback)
