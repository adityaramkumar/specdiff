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
  cli/              # Click commands, one module per area
  config.py         # .specdiff/config.yaml loader
  parser.py         # Spec file parser (frontmatter + SHA-256 hashing)
  graph.py          # Spec graph: depends_on and parent edges, topological sort
  plan.py           # Fingerprints, staleness reasons, build order
  hashmap.py        # .specdiff/hash-map.json store, hand-edit detection
  skills.py         # Built-in skills with per-project overrides
  default_skills/   # Built-in stage prompts (plan, implement, test, repair, review, spec-eval)
  providers/        # One module per LLM provider (gemini, claude, openai_compat)
  llm.py            # generate_content() facade + extract_json()
  agents/
    context.py      # NodeContext and the shared prompt prefix
    fileblocks.py   # <file path="..."> output format
    stages.py       # plan / implement / test / repair / review calls
    pipeline.py     # Per-node loop: generate, check, repair
    spec_agent.py   # Spec review (specdiff review)
  build/
    project.py      # Builds a NodeContext from the hash map and disk
    checks.py       # Static checks and command runs
    files.py        # Paths, headers, backup/restore, NodeWriter
    runner.py       # Per-node build loop with isolated rollback
  extract.py        # Reverse-engineer existing code into spec files
```

## Pipeline Architecture

For each stale spec, in prerequisite order:

```
plan -> (implement || test) -> checks -> [repair -> checks]* -> review
```

- **Plan** returns `<code>`/`<test>` entries and an `<interface>` block: the exact names, signatures and error messages that code and tests must share.
- **Implement** and **test** run in parallel from the plan. Tests never see the implementation.
- **Checks** (`build/checks.py`, `agents/pipeline.py`) run cheapest first: path and ownership, Python syntax, `check_command`, `test_command`. The LLM review only runs after these pass.
- **Repair** receives the failing check's real output and may change or `<delete>` this spec's own files.
- The runner commits each spec as soon as it passes. A failing spec is rolled back alone; its dependents are skipped.

All stages return files as `<file path="...">` blocks (`agents/fileblocks.py`). Never route generated code through JSON.

Testing tip: `tests/fake_llm.py` stands in for every provider by replying per (spec, stage). Patch `specdiff.agents.stages.complete` with it (the `fake_llm` fixture does) and the real parsing, checks, file writes and repair loop all run.

## How to Contribute

1. **Bug fixes** -- open an issue first, then submit a PR with a test that reproduces the bug.
2. **New features** -- discuss in an issue before writing code. The phased build plan in [DESIGN.md](DESIGN.md) describes what's planned.
3. **Examples** -- new example projects in `examples/` are welcome. Each should be self-contained with its own `.specdiff/` directory and a `test_command` that actually finds its tests.
4. **Skills** -- improvements to `src/specdiff/default_skills/` that produce better generation output.

## Code Style

- Python 3.10+
- Ruff for linting and formatting (config in `pyproject.toml`)
- No comments that just narrate what the code does
- Keep files under 150 lines where possible
