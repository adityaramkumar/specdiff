"""Score the build pipeline on small spec projects with hidden tests.

Each case in evals/cases/ has:
  specs/         copied to .specdiff/ and built
  hidden_tests/  run after the build; agents never see them
  reference/     a known-good solution (case.yaml maps specs to its files);
                 tests/test_evals.py checks it passes the hidden tests

    python -m evals.run --model claude-opus-5-5 [--case slugify] [--repeat 3]

Needs the model's API key. Results are printed and saved under evals/results/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from specdiff import hashmap
from specdiff.build.runner import execute_build
from specdiff.config import load_config
from specdiff.graph import build_graph
from specdiff.parser import discover_specs
from specdiff.plan import compute_states, plan_build, skills_hash

CASES = Path(__file__).parent / "cases"
RESULTS = Path(__file__).parent / "results"
PYTEST = f"{sys.executable} -m pytest -q -p no:cacheprovider"


@dataclass
class CaseResult:
    case: str
    specs: int
    built: int
    repairs: int
    hidden_passed: int
    hidden_total: int
    llm_calls: int
    input_tokens: int
    output_tokens: int
    seconds: float

    @property
    def score(self) -> float:
        return self.hidden_passed / self.hidden_total if self.hidden_total else 0.0


@contextmanager
def in_dir(path: Path) -> Iterator[None]:
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def hidden_results(tests_dir: Path, import_root: Path) -> tuple[int, int]:
    """Run hidden tests against code in import_root. Returns (passed, total collected)."""
    junit = tests_dir.parent / "hidden-junit.xml"
    subprocess.run(
        f"PYTHONPATH={import_root} {PYTEST} {tests_dir} --junitxml={junit}",
        shell=True,
        capture_output=True,
    )
    if not junit.exists():
        return 0, 0
    root = ET.parse(junit).getroot()
    suite = root if root.tag == "testsuite" else root[0]
    total = int(suite.get("tests", 0))
    bad = sum(int(suite.get(k, 0)) for k in ("failures", "errors", "skipped"))
    return total - bad, total


def run_case(case: Path, model: str, max_retries: int = 2) -> CaseResult:
    # Collection errors hide how many tests exist, so count them against the reference.
    _, expected = hidden_results(case / "hidden_tests", case / "reference")
    with tempfile.TemporaryDirectory() as tmp, in_dir(Path(tmp)):
        specs_dir = Path(".specdiff")
        shutil.copytree(case / "specs", specs_dir)
        config_data = {
            "model": model,
            "language": "python",
            "test_framework": "pytest",
            "test_command": f"PYTHONPATH=src {PYTEST} src",
            "max_retries": max_retries,
        }
        (specs_dir / "config.yaml").write_text(yaml.safe_dump(config_data))
        config = load_config(specs_dir)
        graph = build_graph(discover_specs(specs_dir))
        hm = hashmap.load(specs_dir)
        states = compute_states(graph, hm, config, skills_hash(specs_dir))
        order = plan_build(graph, states).order

        start = time.monotonic()
        report = execute_build(
            [graph.nodes[n] for n in order], config, hm, graph, specs_dir,
            inputs={n: states[n].inputs for n in order},
        )  # fmt: skip
        seconds = time.monotonic() - start

        shutil.copytree(case / "hidden_tests", "hidden_tests")
        passed, _ = hidden_results(Path("hidden_tests"), Path("src"))
    return CaseResult(
        case=case.name,
        specs=len(graph.nodes),
        built=len(report.built),
        repairs=report.repairs,
        hidden_passed=passed,
        hidden_total=expected,
        llm_calls=report.usage.calls,
        input_tokens=report.usage.input_tokens,
        output_tokens=report.usage.output_tokens,
        seconds=round(seconds, 1),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("--case", action="append", help="Run only these cases")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args()

    cases = sorted(p for p in CASES.iterdir() if (p / "specs").is_dir())
    if args.case:
        cases = [c for c in cases if c.name in args.case]
    results = [
        run_case(case, args.model, args.max_retries) for case in cases for _ in range(args.repeat)
    ]

    row = "{:<12} {:>7} {:>8} {:>9} {:>18} {:>6}"
    print("\n" + row.format("case", "built", "repairs", "hidden", "tokens in/out", "secs"))
    for r in results:
        print(row.format(
            r.case, f"{r.built}/{r.specs}", r.repairs, f"{r.hidden_passed}/{r.hidden_total}",
            f"{r.input_tokens:,}/{r.output_tokens:,}", r.seconds,
        ))  # fmt: skip
    passed = sum(r.hidden_passed for r in results)
    total = sum(r.hidden_total for r in results)
    print(f"\nHidden tests passed: {passed}/{total} ({passed / total:.0%})" if total else "")

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"{stamp}-{args.model}.json"
    out.write_text(json.dumps([asdict(r) | {"model": args.model} for r in results], indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
