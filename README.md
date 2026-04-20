# Specdiff

[![CI](https://github.com/adityaramkumar/specdiff/actions/workflows/ci.yml/badge.svg)](https://github.com/adityaramkumar/specdiff/actions/workflows/ci.yml)
[![Design Doc](https://img.shields.io/badge/docs-Design-blue)](DESIGN.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Spec-driven code generation. The spec is the source of truth, code is a build artifact.

Write short, human-readable specs. Specdiff generates the code, tracks what changed, and rolls back if tests fail. When a contract spec changes, everything downstream is automatically rebuilt in the right order.

## Install

```bash
pip install -e ".[dev]"
```

Set your Gemini API key:

```bash
export GEMINI_API_KEY=your-key-here
```

## Project Setup

Create a `.specdiff/` directory in your project root with a config and your specs:

```
your-project/
  .specdiff/
    config.yaml
    skills/
      architect.skill.md
      interface.skill.md
      implementation.skill.md
      testing.skill.md
      review.skill.md
      spec-eval.skill.md
    contracts/
      api/users.spec.md
    behaviors/
      auth/
        login.spec.md
        signup.spec.md
```

Run `specdiff init` to scaffold the directory with a `config.yaml` and all required skill files automatically.

Minimal `config.yaml`:

```yaml
model: gemini-2.5-flash
output_dir: src
specs_dir: .specdiff
language: python
```

Each spec file is Markdown with YAML frontmatter:

```yaml
---
id: behaviors/auth/login
version: "1.0.0"
parent: auth
status: approved
depends_on:
  - contracts/api/users
---
```

Everything below the frontmatter is your spec -- prose, code snippets, whatever communicates the intent.

## Examples

Four generated example snapshots in [`examples/`](examples/), each with specs and generated output:

| Example | What it demonstrates |
|---|---|
| [`rest-api/`](examples/rest-api) | Auth + user management API. Dependency graph, cascade rebuilds, error handling specs. |
| [`cli-tool/`](examples/cli-tool) | CSV/JSON file converter. Non-web use case, input/output contracts, code-in-spec. |
| [`fullstack-todo/`](examples/fullstack-todo) | Todo app with backend + frontend. Cross-layer dependencies, component specs. |
| [`data-pipeline/`](examples/data-pipeline) | Event processing ETL. Sequential pipeline specs, schema contracts, multi-step dependencies. |

These examples are primarily for inspecting generated structure and spec relationships. They are not currently packaged as fully runnable standalone apps.

Skill files in each example's `.specdiff/skills/` are copies of the files in `examples/shared-skills/`. Update `shared-skills/` when improving skill content, then copy the changes into each example.

## How to Retrofit an Existing Codebase

Specdiff is designed for spec-first development, but you can bootstrap it onto a larger, existing project using the Graph UI.

1. **Initialize Config:** Create a `.specdiff/config.yaml` at your project root.
2. **Reverse-Engineer Specs:** Use an AI coding assistant (like Cursor, Copilot, or Claude) to read your existing code and generate Markdown specs for your core features. Place these in `.specdiff/behaviors/` or `.specdiff/contracts/`.
3. **Link the Graph:** Ensure each generated spec has proper YAML frontmatter with `id`, `version`, and crucially, a `depends_on` array linking it to other specs.
    ```yaml
    ---
    id: behaviors/user_authentication
    version: 1.0.0
    parent: behaviors
    depends_on:
      - contracts/database/users_table
    ---
    ```
4. **Visualize:** Run `specdiff ui` and open `localhost:8000`. As you add more spec files and link them, the interactive graph will automatically update, allowing you to map out your system architecture visually before you start using Specdiff for future code generation.

## Commands

### `specdiff build [node_id]`

Generate code from specs. Only stale nodes are rebuilt. If a spec depends on a changed contract, it's automatically included in the cascade.

```
$ specdiff build
Building 3 node(s)...

  [contracts/api/users] running swarm...
  [contracts/api/users] done.
  [behaviors/auth/login] running swarm...
  [behaviors/auth/login] done.
  [behaviors/auth/signup] running swarm...
  [behaviors/auth/signup] done.

Build complete.
```

If the review agent rejects an implementation, the swarm retries automatically (up to `max_retries` times) with the critique fed back as context. If tests fail after generation, all files are rolled back.

Use `--no-review` to skip the review gate and always write the generated output. Use `specdiff build <node_id>` to target a single node.

Use `--dry-run` to preview the full build plan (nodes, order, reason) without invoking any LLM:

```
$ specdiff build --dry-run
Would build 3 node(s) in this order:

  1. contracts/api/users  [stale]
  2. behaviors/auth/login  [stale, depends on contracts/api/users]
  3. behaviors/auth/signup  [cascade, depends on contracts/api/users]
```

### `specdiff status`

Show which specs are current, stale, or new.

```
$ specdiff status
Node ID                             Status     Version
------------------------------------------------------------
contracts/api/users                 current    1.0.0
behaviors/auth/login                current    1.0.0
behaviors/auth/signup               stale      1.0.0
```

### `specdiff impact [node_id]`

Preview the blast radius of pending changes before building -- no API calls, no generation.

```
$ specdiff impact
Stale spec nodes:
  contracts/api/users

Downstream nodes affected:
  behaviors/auth/login              (cascade depth 1)
  behaviors/auth/signup             (cascade depth 1)

Total: 3 node(s) will be rebuilt
```

### `specdiff review [node_id]`

Run the Spec Agent to check if specs are clear enough for generation. Requires a skill file at `.specdiff/skills/spec-eval.skill.md`.

```
$ specdiff review behaviors/auth/login
Reviewing behaviors/auth/login...
  PASSED: All criteria met. Edge cases documented.
```

If a spec fails, a suggested revision is written to `.specdiff/proposed/` for you to review and adopt.

### `specdiff ui`

Launch an interactive, visual graph of your specs in the browser. 

```
$ specdiff ui --port 8000
Starting Specdiff Graph UI Server at http://localhost:8000
```

The UI displays the dependency graph, visualizes stale/current status, and shows the cascade depth blast radius for any potential changes. It automatically polls for changes as you edit specs.

### `specdiff clean [node_id]`

Delete generated files tracked in the hash map and remove their entries, so they will be fully rebuilt on the next `specdiff build`. Useful after changing agents, skill files, or models.

```
$ specdiff clean
Remove 3 node(s) and 6 generated file(s) from the hash map? [y/N]: y
  [contracts/api/users] cleaned (2 file(s) removed)
  [behaviors/auth/login] cleaned (2 file(s) removed)
  [behaviors/auth/signup] cleaned (2 file(s) removed)

Clean complete.
```

Use `specdiff clean <node_id>` to clean a single node. Use `--yes` to skip the confirmation prompt.

### `specdiff extract [source]`

Read existing code and generate spec files. This is useful for reverse-engineering an existing codebase into Specdiff specs.

```
$ specdiff extract .
Analyzing codebase in ....
Sending payload to LLM to extract contracts...
  Created contracts/models/user.spec.md
Extracting behaviors and dependencies...
  Created behaviors/auth/login.spec.md
Extraction complete! Initialized 2 specs in .specdiff.
```

## Configuration

| Field | Default | Description |
|---|---|---|
| `model` | `gemini-2.5-flash` | LLM model for generation and review. Gemini models use the ADK pipeline; xAI (`grok-*`) models use the OpenAI-compatible path. |
| `output_dir` | `src` | Where generated files are written |
| `specs_dir` | `.specdiff` | Where spec files live |
| `language` | `python` | Target programming language for code generation |
| `test_framework` | (none) | Test framework hint passed to agents (e.g. `pytest`, `vitest`) |
| `test_command` | (none) | Shell command to run before and after generation. Required when generated tests are present. |
| `review_before_build` | `false` | Require spec review to pass before build |
| `max_retries` | `2` | How many times to retry a failing swarm before giving up. On each retry the review critique is fed back into the prompt. |

## How It Works

1. Each spec has a SHA-256 hash of its body content plus graph-shaping frontmatter like dependencies and version
2. A hash map (`.specdiff/hash-map.json`) tracks which hash produced which files
3. On build, only specs with changed hashes are regenerated
4. Specs declare dependencies via `depends_on` — changing a contract cascades to all dependents
5. When building a node, the actual generated code of its dependencies is included in the prompt so the implementation agent sees real API shapes
6. The multi-agent swarm runs: Architect → Interface Planner → (Implementation ‖ Testing) → Review
7. If the Review agent rejects the output, the swarm retries up to `max_retries` times with the critique fed back as context
8. Every generated file gets a traceability header linking it back to its spec
9. If generated tests exist, Specdiff requires a configured `test_command` and runs it before and after generation
10. If tests fail after generation, all files are rolled back to their previous state

For the broader design vision and planned extensions beyond the current implementation, see [DESIGN.md](DESIGN.md).

## Development

### UI

![Specdiff Graph UI](docs/images/ui-screenshot.jpeg)

```bash
# Run tests
pytest tests/ -v

# Lint and format
ruff check src/ tests/
ruff format src/ tests/
```

## License

MIT
