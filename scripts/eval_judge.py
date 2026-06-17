#!/usr/bin/env python
"""Batch evaluation: how often does the metaphor pipeline beat the baseline?

Turns the LLM-as-Judge into the single number the poster reviewers asked for: a
**win-rate**. For each problem we run the full pipeline (Definer → Transformer →
Explorer → Translator), generate the direct baseline, and have the judge compare
them blind — ``--runs`` times per problem, each run reshuffling the A/B order to
control position bias. Aggregated:

    win-rate = (metaphor wins + 0.5 * ties) / N

The actual work lives in ``metaphor_machine.evaluation`` so the Streamlit
Evaluation mode and this CLI stay in sync.

Usage
-----
    # smoke test, no API key, no real calls:
    METAPHOR_MOCK=1 python scripts/eval_judge.py

    # real run, 5 judge passes per problem, pick the model:
    python scripts/eval_judge.py --runs 5 --model anthropic/claude-sonnet-4-6

    # your own problems file (same shape as tests/fixtures/problems.yaml):
    python scripts/eval_judge.py --problems my_problems.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Make `src/` importable when run as a plain script from the repo root.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from metaphor_machine.evaluation import run_evaluation  # noqa: E402

_DEFAULT_PROBLEMS = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "problems.yaml"
)


def load_problems(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text())
    return data.get("problems", [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problems", type=Path, default=_DEFAULT_PROBLEMS)
    ap.add_argument("--metaphors", type=int, default=3, help="candidates per problem")
    ap.add_argument("--moves", type=int, default=3, help="explorer moves per problem")
    ap.add_argument("--runs", type=int, default=3, help="judge passes per problem")
    ap.add_argument("--model", default=None, help="LiteLLM model string (else default)")
    ap.add_argument("--language", default=None, help="en | de")
    args = ap.parse_args()

    problems = load_problems(args.problems)
    if not problems:
        print(f"No problems found in {args.problems}", file=sys.stderr)
        return 1

    print(
        f"Evaluating {len(problems)} problem(s) "
        f"(metaphors={args.metaphors}, moves={args.moves}, runs={args.runs}, "
        f"model={args.model or 'default'})\n"
    )

    def _progress(done: int, total: int, label: str) -> None:
        if label != "done":
            print(f"  [{done + 1}/{total}] {label} …")

    report = run_evaluation(
        problems,
        model=args.model,
        language=args.language,
        n_metaphors=args.metaphors,
        moves=args.moves,
        runs=args.runs,
        progress=_progress,
    )

    print("\n  Per problem:")
    for pp in report["per_problem"]:
        if "error" in pp:
            print(f"    {pp['id']:<24} ERROR: {pp['error']}")
            continue
        s = pp["summary"]
        print(
            f"    {pp['id']:<24} win-rate {s['win_rate']:.0%}  "
            f"(M {s['counts']['metaphor']} / B {s['counts']['baseline']} / "
            f"T {s['counts']['tie']})  [{pp['domain']}]"
        )

    o = report["overall"]
    if o["n"] == 0:
        print("\nNo successful evaluations.", file=sys.stderr)
        return 1

    print("\n" + "=" * 52)
    print("OVERALL")
    print("=" * 52)
    print(f"  metaphor wins : {o['counts']['metaphor']}")
    print(f"  baseline wins : {o['counts']['baseline']}")
    print(f"  ties          : {o['counts']['tie']}")
    print(f"  judge passes  : {o['n']}")
    print(f"\n  WIN-RATE (metaphor, ties=0.5): {o['win_rate']:.0%}")

    if o["per_criterion"]:
        print("\n  Per-criterion (metaphor / baseline / tie):")
        for crit, c in o["per_criterion"].items():
            print(f"    {crit:<14} {c['metaphor']} / {c['baseline']} / {c['tie']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
