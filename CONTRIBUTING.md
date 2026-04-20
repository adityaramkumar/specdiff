# Contributing to Specdiff

Thanks for your interest in contributing. Before diving in, please read the [Design Document](DESIGN.md) -- it explains the system's architecture, the spec graph, the multi-agent swarm, and the design decisions behind them.

## Getting Started

```bash
git clone git@github.com:adityaramkumar/specdiff.git
cd specdiff
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Development Workflow

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

All changes must pass CI (lint + tests) before merging.

## Project Structure

```
src/specdiff/
  cli.py          # Click CLI commands (build, status, impact, review, ui, extract, init)
  parser.py       # Spec file parser (frontmatter + SHA-256 hashing)
  graph.py        # Dependency graph, topological sort, cascade walk
  hashmap.py      # Hash map store (.specdiff/hash-map.json)
  runner.py       # Build orchestration: retry loop, backup/restore, test gating
  skills.py       # Skill file loader (discovers *.skill.md from specs_dir/skills/)
  llm.py          # LLM client (Gemini + xAI/OpenAI-compatible) + JSON extraction
  types.py        # Dataclasses: SpecNode, SpecdiffConfig, HashMap, SwarmResult, FilePlan
  extract.py      # Reverse-engineer existing code into spec files
  agents/
    spec_agent.py # Spec review agent (specdiff review command)
    swarm.py      # Multi-agent pipeline (ADK path for Gemini, custom path for xAI)
```

## Pipeline Architecture

The build pipeline runs four stages in sequence for each spec node:

```
Architect → Interface Planner → (Implementation ‖ Testing) → Review
```

- **Architect**: produces a JSON map of `{file_path: responsibility}` — the file plan.
- **Interface Planner**: produces a JSON map of `{file_path: interface_definition}` — exact signatures and type annotations before any implementation is written.
- **Implementation** and **Testing** run in parallel. Implementation writes code; Testing writes a test suite. Both see the interface spec from the previous stage.
- **Review**: checks that the generated code satisfies every requirement in the spec. Returns `{"passed": bool, "feedback": str}`.

If Review rejects the output, the critique is injected back into the prompt and the whole pipeline retries (up to `max_retries` times, configurable in `config.yaml`). After `max_retries` exhausted with `--no-review`, the build continues with a warning; without it, the build fails and rolls back.

### Dependency Code Context

When building a node that has `depends_on` entries, the runner reads the already-generated files for each dependency from disk and injects them into the prompt as `--- DEPENDENCY IMPLEMENTATION ---` sections. This gives the Implementation agent real API shapes to code against, not just spec prose.

### Two LLM Backends

`swarm.py` dispatches on the model name prefix:

- **Gemini models** (`gemini-*`): uses the Google ADK pipeline (`SequentialAgent`, `ParallelAgent`, `InMemoryRunner`). Each agent's `output_key` is written to session state.
- **xAI / OpenAI-compatible models** (`grok-*`, etc.): uses a custom `ThreadPoolExecutor`-based pipeline in `_run_pipeline_custom`. Each stage appends its output to a growing context string.

Both backends share the same `_build_prompt` function and `run_swarm` entry point.

## How to Contribute

1. **Bug fixes** -- open an issue first, then submit a PR with a test that reproduces the bug.
2. **New features** -- discuss in an issue before writing code. The phased build plan in [DESIGN.md](DESIGN.md) describes what's planned.
3. **Examples** -- new example projects in `examples/` are welcome. Each should be self-contained with its own `.specdiff/` directory. Copy the skill files from `examples/shared-skills/` into the example's `.specdiff/skills/`.
4. **Skill files** -- improvements to the example skill files in `examples/shared-skills/` that produce better generation output.

## Code Style

- Python 3.10+
- Ruff for linting and formatting (config in `pyproject.toml`)
- No comments that just narrate what the code does
- Keep files under 150 lines where possible
