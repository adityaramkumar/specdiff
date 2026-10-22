"""Files written by `specdiff init`."""

INIT_CONFIG = """\
# Model prefixes: gemini-* (GEMINI_API_KEY), claude-* (ANTHROPIC_API_KEY),
# gpt-*/o* (OPENAI_API_KEY), grok-* (XAI_API_KEY).
model: gemini-2.5-flash
output_dir: src
specs_dir: .specdiff
language: python
test_framework: pytest
# Run after every spec is generated; failures are fed back to the repair stage.
test_command: PYTHONPATH=src python -m pytest -q src
# Optional extra check, e.g. a typechecker: check_command: npx tsc --noEmit
review_before_build: false
# Repair attempts per spec when a check fails.
max_retries: 2
"""

SKILLS_README = """\
# Skills

Each build stage runs with a built-in prompt ("skill"): plan, implement, test,
repair, review, plus spec-eval for `specdiff review`.

To customise one, print the built-in version into this folder and edit it:

    specdiff skill implement > .specdiff/skills/implement.skill.md

A file here replaces the built-in skill. Changing a build skill marks every spec
stale, since it changes what the generated code would be.
"""

EXAMPLE_SPEC = """\
---
id: behaviors/hello
version: "1.0.0"
status: approved
---

## Hello World

Replace this with your first real spec.

### Acceptance Criteria

- `greet(name)` returns "Hello, <name>!"
- If name is empty or only whitespace, it returns "Hello, World!"
- Name is stripped of leading and trailing whitespace before use
"""
