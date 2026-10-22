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

Set the API key for the model you configure:

| Model prefix | Provider | Environment variable |
|---|---|---|
| `gemini-*` | Google | `GEMINI_API_KEY` |
| `claude-*` | Anthropic | `ANTHROPIC_API_KEY` |
| `gpt-*`, `o1*`, `o3*`, `o4*` | OpenAI | `OPENAI_API_KEY` |
| `grok-*` | xAI | `XAI_API_KEY` |

## Project Setup

Create a `.specdiff/` directory in your project root with a config and your specs:

```
your-project/
  .specdiff/
    config.yaml
    skills/              # optional overrides of the built-in agent prompts
    contracts/
      api/users.spec.md
    behaviors/
      auth/
        login.spec.md
        signup.spec.md
```

Run `specdiff init` to scaffold the directory with a `config.yaml` and an example spec.

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

Set `generate: false` for a spec that only provides context, such as a constitution of project-wide conventions or a list of security constraints. It is never built, but its text reaches every spec that names it as `parent` or in `depends_on`, and editing it marks them stale.

### Acceptance tests

Generated tests are written by the same model that writes the code, so passing them only shows the model agrees with itself. To pin down behavior yourself, write the tests and list them on the spec:

```yaml
---
id: behaviors/auth/login
version: "1.0.0"
status: approved
acceptance:
  - tests/acceptance/test_login.py
---
```

Acceptance tests are the contract. Agents see them, can never write them, and a spec is only saved once they pass; a failure goes to the repair stage with the instruction to fix the code. Editing an acceptance test marks its spec stale.

They run as `acceptance_command` (default: `test_command`) with the files appended, so keep them somewhere your `test_command` doesn't already collect -- otherwise the baseline run fails before their spec is built. Write them before the code exists and `specdiff build` becomes test-driven.

## Examples

Four generated example snapshots in [`examples/`](examples/), each with specs and generated output:

| Example | What it demonstrates |
|---|---|
| [`rest-api/`](examples/rest-api) | Auth + user management API. Dependency graph, cascade rebuilds, error handling specs. |
| [`cli-tool/`](examples/cli-tool) | CSV/JSON file converter. Non-web use case, input/output contracts, code-in-spec. |
| [`fullstack-todo/`](examples/fullstack-todo) | Todo app with backend + frontend. Cross-layer dependencies, component specs. |
| [`data-pipeline/`](examples/data-pipeline) | Event processing ETL. Sequential pipeline specs, schema contracts, multi-step dependencies. |

These are snapshots produced by an earlier version of the pipeline, kept as a record. When they were audited, many of their generated tests failed; [docs/example-audit.md](docs/example-audit.md) explains why, and how the current pipeline addresses each cause.

## How to Retrofit an Existing Codebase

1. Run `specdiff init`, then point `output_dir` and `test_command` at your project.
2. Run `specdiff extract --source <your code>`. It writes a `constitution` spec summarising the codebase's architecture and conventions, plus contract and behavior specs that inherit from it. Everything it writes is a **draft**, and it never overwrites an existing spec.
3. Read each draft. Fix what the model misread, add acceptance tests for behavior you care about, then set `status: approved`.
4. Run `specdiff ui` to see the graph as you link specs together.

Specdiff never overwrites a file it did not generate, so building an approved spec will not clobber the existing code it describes. Use specs for new and rewritten parts first, and retire the old code for a spec once its generated replacement passes.

## Commands

### `specdiff build [node_id]`

Generate code for stale specs, prerequisites first. Each spec goes through:

1. **Plan** -- files, and the exact public interface (signatures, error messages) code and tests must share.
2. **Implement** and **test**, in parallel. Tests are written from the spec and plan, not from the code.
3. **Checks** -- path and ownership rules, Python syntax, your `check_command`, then your `test_command`.
4. **Repair** -- any failing check's real output goes back to the model, up to `max_retries` times.
5. **Review** -- once checks pass, an LLM confirms the code does everything the spec asks and nothing more.

```
$ specdiff build
Building 2 node(s)...

  [contracts/api/users] planning
  [contracts/api/users] writing code and tests
  [contracts/api/users] running tests
  [contracts/api/users] reviewing
  [contracts/api/users] done: 4 file(s), 0 repair(s), 4 LLM call(s), 6,210 in / 2,904 out tokens
  [behaviors/auth/login] planning
  [behaviors/auth/login] writing code and tests
  [behaviors/auth/login] running tests
  [behaviors/auth/login] repairing (1/2): Tests failed: `PYTHONPATH=src python -m pytest -q src`
  [behaviors/auth/login] running tests
  [behaviors/auth/login] reviewing
  [behaviors/auth/login] done: 3 file(s), 1 repair(s), 5 LLM call(s), 14,880 in / 4,120 out tokens

Built 2, failed 0, skipped 0. 9 LLM call(s), 21,090 in / 7,024 out tokens.
```

Each spec is saved as soon as it passes. If one fails, only its files are rolled back and only specs downstream of it are skipped; everything else still builds.

Every prompt includes the project's file map. A spec may not write a file another spec owns, or any existing file specdiff did not generate.

Specdiff records a hash of every file it writes. If you edit a generated file by hand, `build` refuses to overwrite it and lists the edited files (so does `status`). Move the change into the spec, or pass `--force` to overwrite.

Use `--no-review` to skip the LLM review stage. Use `specdiff build <node_id>` to build one node and whatever it needs.

Use `--dry-run` to preview the full build plan (nodes, order, reason) without invoking any LLM:

```
$ specdiff build --dry-run
Would build 3 node(s) in this order:

  1. contracts/api/users  [spec changed]
  2. behaviors/auth/login  [contracts/api/users changed]
  3. behaviors/auth/signup  [contracts/api/users changed]
```

### `specdiff status`

Show which specs are current, stale, or new, and why. A node is stale when anything that shaped its code changed: its own spec, a dependency or parent spec (transitively), the skill files, or the model/language/test settings.

```
$ specdiff status
Node ID                             Status     Version    Why
--------------------------------------------------------------------------------
contracts/api/users                 stale      1.0.1      spec changed
behaviors/auth/login                stale      1.0.0      contracts/api/users changed
behaviors/auth/signup               current    1.0.0
```

Specs with `status: draft` are never built, and neither is anything downstream of a stale draft.

### `specdiff impact [node_id]`

Preview what a build would touch -- no API calls, no generation. With `node_id`, show the blast radius of changing that spec.

```
$ specdiff impact contracts/api/users
Changing contracts/api/users rebuilds:
  behaviors/auth/login                (cascade depth 1)
  behaviors/auth/signup               (cascade depth 1)

Total: 3 node(s)
```

### `specdiff review [node_id]`

Run the Spec Agent to check if specs are clear enough for generation: exact error messages, counts, validation rules, output formats.

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

### `specdiff validate`

Check the spec graph for errors before running a build. Reports all issues at once — missing `depends_on` references, missing `parent` references, duplicate IDs, and circular dependencies. Exits with code 1 if any errors are found, making it usable as a CI gate.

```
$ specdiff validate
Found 2 error(s):

  behaviors/auth/login: depends_on 'contracts/api/nonexistent' not found
  behaviors/auth/signup: parent 'auth' not found
```

On a clean graph:

```
$ specdiff validate
Validated 5 spec(s). No issues found.
```

### `specdiff extract [--source DIR] [--granularity auto|file]`

Draft specs from existing code: a context-only `constitution` spec with the codebase's conventions, then contract and behavior specs that inherit from it (`--granularity file` writes one spec per source file instead). All of them start as `status: draft`, so nothing is built until you review and approve them. Existing spec files are never overwritten.

## Configuration

| Field | Default | Description |
|---|---|---|
| `model` | `gemini-2.5-flash` | Model for every stage; the prefix picks the provider (see Install) |
| `output_dir` | `src` | Where generated files are written; also the import root agents are told to use |
| `specs_dir` | `.specdiff` | Where spec files live |
| `language` | `python` | Target language (a spec's `language` field overrides it) |
| `test_framework` | (none) | Test framework named to agents (e.g. `pytest`, `vitest`) |
| `test_command` | (none) | Run after each spec is generated, and once before the build as a baseline. Without it, no tests are generated and output is unverified. |
| `check_command` | (none) | Extra command that must pass, e.g. `npx tsc --noEmit` |
| `acceptance_command` | `test_command` | Runs a spec's acceptance tests, with their paths appended |
| `review_before_build` | `false` | Require spec review to pass before build |
| `max_retries` | `2` | Repair attempts per spec after a failed check |

## Skills

Each stage runs with a built-in prompt: `plan`, `implement`, `test`, `repair`, `review`, and `spec-eval` for `specdiff review`. To change one, print it into your project and edit it:

```bash
specdiff skill implement > .specdiff/skills/implement.skill.md
```

A file in `.specdiff/skills/` replaces the built-in version. Output formats are enforced by specdiff, not by skills, so a custom skill can't break parsing. Changing a build skill marks every spec stale.

## How It Works

1. Each spec is fingerprinted from its content, its dependencies' and parent's fingerprints, the build skills, and the model/language/test settings. `.specdiff/hash-map.json` records the inputs of the last build, so `status` can say exactly why a spec is stale.
2. Agents see the spec, its parent specs, its dependency specs, the code already generated for its dependencies, its own previous files, and which paths other specs own.
3. Agents return files as `<file path="...">` blocks with verbatim contents. Code never passes through JSON, which models escape incorrectly often enough to corrupt files.
4. Deterministic checks run before any LLM judgement, and their real output drives repair.
5. Every generated file gets a traceability header naming its spec, and every overwritten or deleted file is backed up until its spec's build succeeds.

For the broader design vision and planned extensions beyond the current implementation, see [DESIGN.md](DESIGN.md).

## Evals

`evals/` scores the pipeline end to end on small spec projects with hidden tests the agents never see:

```bash
python -m evals.run --model claude-opus-5-5            # all cases
python -m evals.run --model gemini-2.5-flash --case inventory --repeat 3
```

Each case lists how many specs built, how many repairs it took, how many hidden tests pass, tokens used and time. Run it before and after changing a skill or a stage prompt to see whether the change helped. Results are saved under `evals/results/`. CI runs every case with its reference solution in place of a model, which proves the case is solvable and its hidden tests are right.

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
