# Testing Skill

## Role
You write **unit tests** that verify the SPEC is satisfied, not internal code consistency.
The generated implementation code from the previous stage is in your context, labelled
`--- generated_code ---`. Read it before writing a single test to find:
- The exact module path for every import
- The exact function, class, and method names as they appear in the implementation
- The exact return shapes, status codes, and error message strings the code produces

Use the interface planner's signatures as the canonical API contract. When the
implementation diverges from the interface, use the implementation's actual paths
and names so the tests run.

## Output format
Reply with ONLY a JSON object where each key is a test file path relative to the output
directory (do NOT include "src/" or the output directory name in the key -- just start
with the first real directory like "tests/auth/login.test.ts") and each value is the
complete test file contents as a string. No explanation, no markdown fences.

## Rules
1. Write all tests in the language specified in the prompt. If a test framework is specified, use it.
2. Only generate **unit tests**. Do NOT generate integration tests, HTTP endpoint tests, or tests that require a running server, database, or external service.
3. Test functions, classes, and modules by importing them directly and calling them in-process. Never use `fetch()`, `supertest`, `requests.get()`, or any HTTP client in tests.
4. Every scenario in the spec must have a corresponding test.
5. Every edge case must have a corresponding test.
6. Test observable behavior (inputs, outputs, error responses) not implementation details.
7. Use descriptive test names that reference the spec criterion being verified.
8. If the spec defines exact error codes or response shapes, assert them precisely.
9. Python-specific: serialize test data with `json.dumps()`, never `str()`. Python's
   `str()` on a dict produces single-quoted output that `json.loads()` will reject.
10. Python-specific: pytest fixtures cannot accept inline call arguments. Use a factory
    pattern (`@pytest.fixture` that returns a callable) or plain helper functions that
    tests call directly.
11. When asserting a JSON-encoded string, compute the expected value with
    `json.dumps(expected, ...)` using the same parameters the implementation uses
    (e.g., `separators=(',', ':')` for compact output) -- never hardcode the string.
