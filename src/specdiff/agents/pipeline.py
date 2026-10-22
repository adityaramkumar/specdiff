from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from specdiff.agents import stages
from specdiff.agents.context import NodeContext
from specdiff.agents.stages import Plan, Usage
from specdiff.build.checks import run_command, static_problems


@dataclass
class PipelineConfig:
    model: str
    skills: dict[str, str]
    max_repairs: int = 2
    review: bool = True
    test_command: str | None = None
    check_command: str | None = None


@dataclass
class NodeOutcome:
    ok: bool
    files: dict[str, str] = field(default_factory=dict)
    error: str = ""
    repairs: int = 0
    usage: Usage = field(default_factory=Usage)


Sync = Callable[[dict[str, str]], object]
Log = Callable[[str], None]


def run_node(ctx: NodeContext, cfg: PipelineConfig, sync: Sync, log: Log) -> NodeOutcome:
    """Plan, generate, check, and repair one node until its checks pass or repairs run out.

    sync writes the current file set to disk so commands can run against it.
    """
    usage = Usage()
    skills, model = cfg.skills, cfg.model

    log("planning")
    plan = stages.plan(ctx, skills["plan"], model, usage)

    # Tests are written from the spec and plan alone, in parallel with the code, so
    # they check the spec rather than echo the implementation.
    log("writing code and tests" if cfg.test_command else "writing code")
    code_usage, test_usage = Usage(), Usage()
    with ThreadPoolExecutor(max_workers=2) as pool:
        code_job = pool.submit(stages.implement, ctx, plan, skills["implement"], model, code_usage)
        test_job = (
            pool.submit(stages.write_tests, ctx, plan, skills["test"], model, test_usage)
            if cfg.test_command and plan.tests
            else None
        )
        code = code_job.result()
        tests = test_job.result() if test_job else None
    usage += code_usage
    usage += test_usage

    files = {p: ctx.own_files[p] for p in code.unchanged if p in ctx.own_files}
    files.update(code.files)
    if tests:
        files.update({p: ctx.own_files[p] for p in tests.unchanged if p in ctx.own_files})
        files.update(tests.files)

    ours = set(ctx.own_files)
    required = set(plan.code)
    for attempt in range(cfg.max_repairs + 1):
        failure = _check(ctx, cfg, plan, required, files, ours, sync, usage, log)
        if failure is None:
            return NodeOutcome(ok=True, files=files, repairs=attempt, usage=usage)
        if attempt == cfg.max_repairs:
            return NodeOutcome(ok=False, files=files, error=failure, repairs=attempt, usage=usage)
        log(f"repairing ({attempt + 1}/{cfg.max_repairs}): {_first_line(failure)}")
        fix = stages.repair(ctx, plan, files, failure, skills["repair"], model, usage)
        files = {p: body for p, body in files.items() if p not in fix.deleted} | fix.files
        required -= set(fix.deleted)
    raise AssertionError("unreachable")


def _check(
    ctx: NodeContext,
    cfg: PipelineConfig,
    plan: Plan,
    required: set[str],
    files: dict[str, str],
    ours: set[str],
    sync: Sync,
    usage: Usage,
    log: Log,
) -> str | None:
    """Return a description of the first failing check, or None if everything passes."""
    problems = static_problems(files, ctx.output_dir, ctx.others, ours)
    missing = sorted(required - files.keys())
    problems += [f"{p} is in the plan but was not written." for p in missing]
    if problems:
        return "Static checks failed:\n" + "\n".join(f"- {p}" for p in problems)

    sync(files)
    ours.update(files)
    for label, command in (("Check", cfg.check_command), ("Tests", cfg.test_command)):
        if not command:
            continue
        log(f"running {label.lower()}")
        passed, output = run_command(command)
        if not passed:
            return f"{label} failed: `{command}`\n\n```\n{output}\n```"

    if cfg.review:
        log("reviewing")
        passed, feedback = stages.review(ctx, plan, files, cfg.skills["review"], cfg.model, usage)
        if not passed:
            return f"Review found spec problems:\n\n{feedback}"
    return None


def _first_line(text: str) -> str:
    return text.strip().splitlines()[0][:120] if text.strip() else ""
