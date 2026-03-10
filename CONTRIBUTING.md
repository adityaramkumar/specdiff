# Contributing to Specanopy

Thanks for your interest in contributing. Before diving in, please read the [Design Document](DESIGN.md) -- it explains the system's architecture, the spec graph, the multi-agent swarm, and the design decisions behind them.

## Getting Started

```bash
git clone git@github.com:adityaramkumar/specanopy.git
cd specanopy
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
src/specanopy/
  cli.py          # Click CLI commands
  parser.py       # Spec file parser (frontmatter + hashing)
  graph.py        # Dependency graph, topo sort, cascade
  hashmap.py      # Hash map store (JSON)
  runner.py       # Build orchestration, backup/restore
  skills.py       # Skill file loader
  llm.py          # Shared Gemini client + JSON extraction
  types.py        # Dataclasses
  agents/
    spec_agent.py   # Spec review agent
    architect.py    # File plan parsing
    swarm.py        # ADK multi-agent pipeline
```

## How to Contribute

1. **Bug fixes** -- open an issue first, then submit a PR with a test that reproduces the bug.
2. **New features** -- discuss in an issue before writing code. The phased build plan in [DESIGN.md](DESIGN.md) describes what's planned.
3. **Examples** -- new example projects in `examples/` are welcome. Each should be self-contained with its own `.specanopy/` directory and a symlink to `shared-skills/`.
4. **Skill files** -- improvements to the example skill files in `examples/shared-skills/` that produce better generation output.

## Code Style

- Python 3.10+
- Ruff for linting and formatting (config in `pyproject.toml`)
- No comments that just narrate what the code does
- Keep files under 150 lines where possible
