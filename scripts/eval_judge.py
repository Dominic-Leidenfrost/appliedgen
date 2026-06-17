#!/usr/bin/env python
"""Batch evaluation: how often does the metaphor pipeline beat the baseline?

This turns the LLM-as-Judge (agents/judge.py) into the single number the poster
reviewers asked for: a **win-rate**. For each seed problem we run the full
pipeline (Definer → Transformer → Explorer → Translator), generate the direct
baseline, and have the judge compare them blind. Aggregated:

    win-rate = (metaphor wins + 0.5 * ties) / N

Usage
-----
    # smoke test, no API key, no real calls:
    METAPHOR_MOCK=1 python scripts/eval_judge.py

    # real run on the built-in problem set:
    python scripts/eval_judge.py --moves 3

    # your own problems file (same shape as tests/fixtures/problems.yaml):
    python scripts/eval_judge.py --problems my_problems.yaml

Notes
-----
* Position bias is controlled inside the judge (randomised A/B per call). We
  pass a per-problem seed so a run is reproducible.
* Ties count as half a win — standard for pairwise preference evaluation.
* This is intentionally a thin script, not a test: it makes real LLM calls and
  costs money/time. Keep it out of the pytest path.
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

from metaphor_machine.core.pipeline import Pipeline  # noqa: E402

_DEFAULT_PROBLEMS = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "problems.yaml"
)


def load_problems(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text())
    return data.get("problems", [])


def evaluate_one(problem_text: str, *, n_metaphors: int, moves: int, seed: int) -> dict:
    """Run the whole pipeline for one problem and judge it against baseline."""
    pipe = Pipeline()
    pipe.run_definer(problem_text)
    candidates = pipe.run_transformer(n=n_metaphors)
    # Curate automatically: take the first candidate (a human would choose here).
    pipe.session.chosen_metaphor = candidates[0]
    for _ in range(moves):
        pipe.run_explorer_turn()
    pipe.run_translator()
    result = pipe.run_judge(seed=seed)
    return {
        "winner": result.winner,
        "order": result.order,
        "criteria": result.criteria_winners,
        "reasoning": result.reasoning,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problems", type=Path, default=_DEFAULT_PROBLEMS)
    ap.add_argument("--metaphors", type=int, default=3, help="candidates per problem")
    ap.add_argument("--moves", type=int, default=3, help="explorer moves per problem")
    args = ap.parse_args()

    problems = load_problems(args.problems)
    if not problems:
        print(f"No problems found in {args.problems}", file=sys.stderr)
        return 1

    print(f"Evaluating {len(problems)} problem(s) "
          f"(metaphors={args.metaphors}, moves={args.moves})\n")

    counts = {"metaphor": 0, "baseline": 0, "tie": 0}
    per_criterion: dict[str, dict[str, int]] = {}

    for i, p in enumerate(problems):
        text = p.get("user_text", "")
        pid = p.get("id", f"problem_{i}")
        try:
            res = evaluate_one(
                text, n_metaphors=args.metaphors, moves=args.moves, seed=i
            )
        except Exception as exc:  # keep going — one bad problem shouldn't sink the run
            print(f"  [{pid}] ERROR: {exc}")
            continue
        counts[res["winner"]] = counts.get(res["winner"], 0) + 1
        for crit, side in res["criteria"].items():
            per_criterion.setdefault(crit, {"metaphor": 0, "baseline": 0, "tie": 0})
            per_criterion[crit][side] = per_criterion[crit].get(side, 0) + 1
        print(f"  [{pid}] winner={res['winner']:<8} (shown {res['order']})")

    n = sum(counts.values())
    if n == 0:
        print("\nNo successful evaluations.", file=sys.stderr)
        return 1

    win_rate = (counts["metaphor"] + 0.5 * counts["tie"]) / n

    print("\n" + "=" * 48)
    print("RESULTS")
    print("=" * 48)
    print(f"  metaphor wins : {counts['metaphor']}")
    print(f"  baseline wins : {counts['baseline']}")
    print(f"  ties          : {counts['tie']}")
    print(f"  N             : {n}")
    print(f"\n  WIN-RATE (metaphor, ties=0.5): {win_rate:.0%}")

    if per_criterion:
        print("\n  Per-criterion (metaphor / baseline / tie):")
        for crit, c in per_criterion.items():
            print(f"    {crit:<14} {c['metaphor']} / {c['baseline']} / {c['tie']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
