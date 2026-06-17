"""Tests for the reusable batch-evaluation module (mock mode)."""

from __future__ import annotations

import os

os.environ.setdefault("METAPHOR_MOCK", "1")

from metaphor_machine.core.schemas import ComparisonResult
from metaphor_machine.evaluation import evaluate_problem, run_evaluation


def test_evaluate_problem_shape():
    ev = evaluate_problem("a team with 12 projects and 2 deadlines", runs=4, moves=1)
    assert ev["summary"]["n"] == 4
    assert len(ev["results"]) == 4
    assert all(isinstance(r, ComparisonResult) for r in ev["results"])
    assert ev["baseline"] and ev["metaphor_answer"]
    assert set(ev["summary"]["counts"]) == {"metaphor", "baseline", "tie"}


def test_run_evaluation_aggregates_over_problems():
    problems = [
        {"id": "p1", "user_text": "too many projects"},
        {"id": "p2", "user_text": "book club with quiet members"},
    ]
    report = run_evaluation(problems, runs=3, moves=1)
    assert len(report["per_problem"]) == 2
    # overall pools every judge run: 2 problems * 3 runs
    assert report["overall"]["n"] == 6
    assert 0.0 <= report["overall"]["win_rate"] <= 1.0
    assert report["params"]["runs"] == 3


def test_run_evaluation_accepts_plain_strings():
    report = run_evaluation(["just one problem"], runs=2, moves=1)
    assert report["per_problem"][0]["id"] == "problem_1"
    assert report["overall"]["n"] == 2


def test_run_evaluation_progress_callback():
    seen = []
    run_evaluation(
        ["x"], runs=1, moves=1, progress=lambda d, t, label: seen.append((d, t, label))
    )
    assert seen and seen[-1][2] == "done"
