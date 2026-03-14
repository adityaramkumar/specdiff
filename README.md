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

Minimal `config.yaml`:

```yaml
model: gemini-3.1-flash-lite-preview
output_dir: src
specs_dir: .specdiff
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

Skill files are shared across examples via symlinks from each example's `.specdiff/skills/` to `examples/shared-skills/`.

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

  [contracts/api/users] generating...
  [contracts/api/users] done.
  [behaviors/auth/login] generating...
  [behaviors/auth/login] done.
  [behaviors/auth/signup] generating...
  [behaviors/auth/signup] done.

Build complete.
```

If the Testing Agent generates tests, `test_command` must be configured so Specdiff can run a baseline before regeneration and verify the regenerated output afterward. If tests fail, all files are rolled back.

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

## Configuration

| Field | Default | Description |
|---|---|---|
| `model` | `gemini-3.1-flash-lite-preview` | Gemini model for generation and review |
| `output_dir` | `src` | Where generated files are written |
| `specs_dir` | `.specdiff` | Where spec files live |
| `test_command` | (none) | Shell command to run before and after generation. Required when generated tests are present. |
| `review_before_build` | `false` | Require spec review to pass before build |

## How It Works

1. Each spec has a SHA-256 hash of its body content plus graph-shaping frontmatter like dependencies and version
2. A hash map (`.specdiff/hash-map.json`) tracks which hash produced which files
3. On build, only specs with changed hashes are regenerated
4. Specs declare dependencies via `depends_on` -- changing a contract cascades to all dependents
5. Every generated file gets a traceability header linking it back to its spec
6. If generated tests exist, Specdiff requires a configured `test_command` and runs it before and after generation
7. If tests fail after generation, all files are rolled back to their previous state

For the broader design vision and planned extensions beyond the current implementation, see [DESIGN.md](DESIGN.md).

## Development

```bash
# Run tests
pytest tests/ -v

# Lint and format
ruff check src/ tests/
ruff format src/ tests/
```

## License

MIT
