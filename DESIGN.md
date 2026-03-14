# Specdiff - Design

> Specdiff turns software development into a compilation problem.
>
> Note: this document describes the target architecture. The current implementation already covers spec parsing, dependency graphs, incremental rebuild tracking, `build`/`status`/`impact`/`review` commands, a basic architect -> implementation/testing -> review swarm, and rollback on failing tests. Independent test specs, reconciler/migration agents, reverse-patch debugging, version-history edges, and user-defined agents are still future work.

```
spec → compile → system
```

Not:

```
code → system
```

---

## Why This Exists

AI coding tools are accelerating code production without changing what the source of truth is. You prompt, code appears, and now you have more of it - faster than before. But it's still code. It still needs to be read, understood, debugged, and maintained. And because it was generated rather than carefully written, it tends to be verbose, over-engineered, and full of patterns nobody explicitly asked for.

The result is that AI makes the existing problem worse. More code. Less understanding. The intent behind the system - what it's supposed to do and why - is nowhere. It was in someone's head when they wrote the prompt, and now it's gone.

The deeper issue is that both humans and AI are now forced to reason about code as the primary artifact. Code is a poor medium for reasoning about intent. It's low-level, noisy, and full of implementation details that obscure behavior. A 500-line file that implements a login flow tells you far less about what the login flow is supposed to do than two paragraphs of well-written spec. Yet the 500-line file is what everyone reads, reviews, and passes to the next AI agent as context.

Specdiff inverts this. The spec is the source of truth - short, human-readable, reasoned about. The code is a build artifact - long, machine-optimized, derived. AI generates *down* from a spec rather than *into* a void. The spec stays small and meaningful. The code stays disposable.

---

## The Spec Graph

Specs form a directed graph. There are three kinds of edges, and each one drives different system behavior:

- **Parent constraint edges** - a child node can add detail but can't contradict its parent. Governs inheritance and validity.
- **Dependency edges** (`depends_on`) - cross-branch relationships between nodes, for example two features that both depend on the same schema. Governs cascade rebuilds and contract propagation.
- **Version edges** - every node change is recorded. Governs history, rollback, and impact analysis.

The hierarchy still exists - the root constitution constrains everything below it - but dependency edges are first-class. Two features depending on the same schema is a normal, expected graph shape, not an exception.

```
project/
  .specdiff/
    constitution.md          <- root: project values, non-negotiables
    intent/                  <- why: goals and user problems
    contracts/               <- what: APIs, schemas, data shapes
    behaviors/               <- how: per-feature logic and edge cases
      auth/
        login.spec.md
        signup.spec.md
    constraints/             <- limits: performance, security, platform
    tests/                   <- independent test specs (see below)
      auth/
        login.test-spec.md
```

The spec format is **not enforced by the system**. Users bring their own - prose, YAML, diagrams, whatever works for their team. Specdiff only requires a minimal header on each node so it can track identity, position in the graph, and dependencies:

```yaml
---
id: auth/login
version: 1.2.0
parent: auth
hash: sha256:a1b2c3...      # auto-generated
depends_on:
  - contracts/api/users
  - constraints/security
status: approved
---
```

Everything else in the file is up to the user.

### Test Specs

Tests live in their own independent folder - separate from behaviors, not nested inside them. A test spec is not a child of the feature it tests; it is an independent node that *references* the feature. This means:

- Test specs can be updated without touching the behavior spec
- The Testing Agent owns the `tests/` folder entirely - implementation agents never touch it
- Test specs can reference multiple behavior nodes, naturally expressing integration tests

```markdown
---
id: tests/auth/login
version: 1.0.0
tests: behaviors/auth/login
depends_on:
  - contracts/api/users
hash: sha256:b3c4d5...
---

## Scenarios

### Happy path
- User submits valid email + password -> receives JWT, redirected to dashboard

### Rate limiting
- 5 failed attempts within 10 minutes -> account locked, error returned

### Edge cases
- Unverified email -> specific banner shown, no JWT issued
- Expired session token -> redirect to login, no silent failure
```

When a behavior spec changes, its linked test specs are flagged as stale and the Testing Agent re-evaluates them. Tests that no longer match a criterion are removed; new criteria get new tests.

---

## Incremental Builds via Hashing

This is the engine of the system. Every spec node has a hash of its content. Specdiff maintains a map of which spec hash produced which code files. When a spec changes, only the stale files are regenerated - nothing else is touched.

```
auth/login spec changes -> hash: a1b2c3 -> f9e8d7

Hash map lookup:
  a1b2c3 -> [src/auth/login.ts, src/auth/login.test.ts]

Result: only those 2 files queued for regeneration.
Everything else: untouched.
```

When a contract node changes (e.g. a schema), Specdiff walks the dependency graph and flags all downstream nodes too - a cascade. Everything affected is automatically queued for regeneration in the right order.

**Safety rules:**
- Never regenerate without a passing test baseline first
- If tests pass before regen but fail after, rollback and retry

### Spec-Level Impact Preview

Before any regeneration runs, Specdiff shows the behavioral blast radius of a spec change - expressed entirely in spec terms, not code terms. The point of the system is that code is an implementation detail; the impact preview reflects this.

```
Spec change detected: behaviors/auth/login v1.2.0 -> v1.3.0

Downstream spec nodes affected:
  tests/auth/login          <- test spec will be re-evaluated
  analytics/login-events    <- depends on login contract
  billing/session-validator <- depends on JWT shape

Cascade depth: 2
```

This is `git diff` for system behavior. Developers reason about the impact in the same language they used to write the spec. Code file changes are derived from this graph automatically and are not shown - they are an output of the system, not an input to human reasoning.

---

## The Multi-Agent Swarm

Once a spec node is approved, a swarm of specialized agents takes over. Each agent has one job and reads its own skill file - a plain Markdown document the team owns and improves over time.

| Agent | Job |
|---|---|
| **Spec Agent** | Reviews and refines spec changes before anything else runs |
| **Architect Agent** | Plans which files need to exist and how they connect |
| **Implementation Agent** | Writes code strictly from the spec and architecture plan |
| **Testing Agent** | Owns the `tests/` folder entirely - derived from test specs, not from code |
| **Review Agent** | Checks generated code actually satisfies its spec |
| **Reconciler Agent** | After a test failure, patches small deltas in place rather than triggering a full retry |
| **Migration Agent** | Produces staged migration files when contract specs change |

### Pipeline

```
Spec change submitted
     |
     v
Spec Agent -> evaluates quality -> refines or approves
     |
     v
Hash map updated -> stale files identified
     |
     v
Architect Agent -> file plan
     |
     +---------------------+---------------------------+
     v                     v                           v
Implementation         Testing Agent           User-defined
Agent -> code      tests written/updated       agents run
     |                     |                           |
     +---------------------+---------------------------+
                           |
                      Suite runs
                           |
                      +----+----+
                    PASS      FAIL
                      |         |
                      |   Reconciler Agent
                      |         |
                      |   +-----+------------------+
                      |  small delta          large/structural failure
                      |  patch in place             |
                      |         |          rollback + retry (x3)
                      +----+----+                   |
                           |         persistent: Spec Agent revision
                    Review Agent
                           |
                         Commit
```

### Skills

Each agent reads a skill file before acting. Think of skill files as the system prompt for each agent in the swarm - they encode what "good" looks like for your project, in your own words, and improve over time independently of the underlying model. The entire behavior of the swarm can be tuned by editing Markdown files, with no changes to the system itself.

The Spec Agent's skill focuses on one thing above all: **ensuring the spec is unambiguous enough to generate behaviorally equivalent code across runs**. A vague spec produces inconsistent output. Full determinism - two agents producing character-for-character identical code - is neither achievable nor the goal. What is achievable is behavioral equivalence: two different implementations that both satisfy the same spec and pass the same test suite are both correct. The spec constrains behavior; the test spec enforces it. Together they define the correctness boundary - the spec alone never could.

```markdown
# .specdiff/skills/spec-eval.skill.md

## Role
You are a senior systems architect reviewing a spec change.
Your primary goal: ensure the spec is specific enough that two
independent agents would produce behaviorally equivalent implementations
from it - meaning both would pass the same test suite derived from this spec.
Structural implementation choices (how code is organized internally) are
acceptable to leave open. Behavioral choices (what the system does, what
it returns, how it handles errors) must be fully specified.
If reasonable people could produce implementations with different observable
behavior, the spec is not ready.

## A spec PASSES if:
- Every acceptance criterion is measurable and unambiguous
  (no "fast", "easy", "good", "appropriate", "handle errors gracefully")
- Every input and output is fully described - types, shapes, constraints
- Every error state has a specified response - no undefined behavior
- At least one edge case is documented per criterion
- All depends_on nodes exist and are approved
- No behavioral choices are left open (structural choices are acceptable)

## A spec FAILS if:
- Any criterion could be implemented in more than one reasonable way
- Error handling is described vaguely ("return an error")
- Response shapes or field names are unspecified
- Performance expectations use relative language ("quickly", "soon")

## On failure:
- Rewrite each failing criterion with specific, concrete language
- Replace vague terms with exact values, types, or behaviors
- Re-evaluate until every criterion is implementation-ready
```

```markdown
# implementation.skill.md
1. Only implement what is in the spec. Nothing more.
2. If anything is ambiguous, stop and flag it - do not guess.
3. Follow the architecture plan from the Architect Agent.
4. If a file's hash is current, do not touch it.
```

```markdown
# testing.skill.md
Tests verify the SPEC is satisfied, not internal code consistency.
Source of truth is the test spec in tests/, not the implementation.

1. Every scenario in the test spec must have a corresponding test.
2. Every edge case must have a corresponding test.
3. When a test spec changes, update tests to match exactly.
4. If previously passing tests fail after regen: rollback and retry.
```

### Extensibility

The agent interface is open. Teams register their own agents by dropping in a skill file and declaring what events trigger them:

- A `screenshot-diff-agent` for UI teams
- A `data-validation-agent` for ML pipelines
- A `compliance-agent` for regulated industries

As shown in the pipeline above, user-defined agents run in parallel with the Implementation and Testing Agents - they are first-class participants in the swarm, not plugins bolted on afterward.

---

## Traceability

Every generated file records the spec node that produced it. This header is injected automatically and never edited by hand.

```typescript
// generated_from: behaviors/auth/login
// spec_hash: f9e8d7
// generated_at: 2025-03-09T10:00:00Z
// agent: implementation-agent-v1.2
```

This makes the system fully auditable. You can always answer "what spec produced this?" and "what does this spec currently produce?" It also enables spec coverage analysis - the Review Agent can verify that every approved spec node has a corresponding generated artifact.

---

## Production Concerns

Four situations require special handling in production: specs that are easier to express in code than English, bugs found in generated files, generation failures that don't warrant a full retry, and stateful database changes. Each has a designed escape hatch that preserves the spec as source of truth.

### Code-in-Spec

When English is more ambiguous than code, use code. The spec is the source of truth about *intent* - not dogmatic about the format that intent takes.

A complex validation rule, a precise algorithm, or an exact formula is legitimately better expressed as a code snippet than as a paragraph of English. Including it directly in the spec keeps it human-authored, versioned, and traceable - without forcing the implementation agent to interpret vague language.

````markdown
## Acceptance Criteria

- Password must pass the following strength check:
  ```python
  def is_strong(password):
      return (len(password) >= 12
          and re.search(r'[A-Z]', password)
          and re.search(r'[0-9]', password)
          and re.search(r'[^a-zA-Z0-9]', password))
  ```
- Weak passwords return HTTP 422 with `{ "error": "password_too_weak" }`
````

The implementation agent reproduces the snippet faithfully; it does not reinterpret it. The system is dogmatic about intent, not about English.

### Debugging and the Reverse Patch

When a developer finds a bug in generated code, they cannot edit the file directly - it will be overwritten on the next regeneration cycle. The fix must live in the spec. But staring at a spec and figuring out which sentence to change is harder than just fixing the obvious line of code.

Specdiff provides a sandbox for this. The developer makes their fix in the generated file locally. An agent diffs the patch against the original and proposes a spec delta - a suggested change to the upstream spec node that would produce that fix.

```
Sandbox patch detected: src/auth/login.ts

Suggested spec delta for behaviors/auth/login:

  - Account locks after 5 failed attempts within 10 minutes
  + Account locks after 3 failed attempts within 5 minutes
    Lock duration: 30 minutes
    Unlock method: manual admin action only
```

The developer reads the suggested spec delta, decides if it accurately captures their intent, and edits it if not. The sandbox patch is then discarded - it was a communication tool, not a fix. The spec change is committed; the corrected code is regenerated from it.

The agent proposes a spec change; it does not author one. Code never becomes the source of truth through the back door.

### Reconciler Agent

The failure path in the pipeline is binary by default - either everything passes or the whole thing rolls back and retries. In practice most failures are small and localized: a wrong error code, a slightly mismatched type, an edge case handled with the right logic but the wrong response shape. These don't warrant a full regeneration cycle.

The Reconciler Agent sits between the test run and the Review Agent. It inspects what failed, measures the delta between what was generated and what the test spec expected, and decides whether to patch in place or escalate.

```
test failure detected
        |
Reconciler Agent inspects delta
        |
   +----+--------------------+
small/local              large/structural
patch in place                |
        |             rollback + retry (x3)
        |                     |
  note recorded    persistent: Spec Agent revision
        |
  continues to Review Agent
```

If it patches, it records what changed and why - this feeds into traceability so the generated file's history is still fully auditable.

The Reconciler also tracks patterns across runs. If it finds itself patching the same class of issue repeatedly, that's a signal the spec is underspecified rather than the generation being unlucky. Repeated patches of the same type route back to the Spec Agent for revision rather than being quietly fixed each time.

### Migration Agent

Changing a contract spec - renaming a field, changing a type, removing a column - is safe for stateless artifacts. The implementation agent regenerates the affected interfaces and routes. But it is dangerous for stateful data. A database cannot be regenerated; it must be migrated.

The Migration Agent handles this as a distinct artifact type. When a contract hash changes, it diffs the old and new schemas and produces a migration file - it does not apply it.

```sql
-- migration: contracts/schemas/user v1.3.0 -> v1.4.0
-- generated_from: contracts/schemas/user
-- spec_hash: f9e8d7
-- STATUS: staged, not applied

ALTER TABLE users RENAME COLUMN email_address TO email;
```

Migration files are staged artifacts. They live in a `migrations/` directory, are committed to version control, and are executed by a deliberate separate action - not automatically on regeneration. Stateless logic can be swapped safely. Stateful data cannot.

The Migration Agent also flags destructive operations explicitly:

```
WARNING: dropping column `legacy_token` - data will be lost.
Confirm this column is unused before applying.
```

---

## What Specdiff Is

1. **A graph store** - spec nodes with hashes, versions, and dependency edges
2. **An agent runtime** - routes work to registered agents when specs change
3. **A minimal contract** - the interface a spec node and an agent must satisfy

The spec format, agent roster, and skill content are all user configuration. Specdiff is the compiler. You write the source.
