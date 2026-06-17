"""Judge agent tests — schema validity, A/B de-anonymisation, pipeline wiring.

All tests run in mock mode (METAPHOR_MOCK=1) so no API key is needed. The mock
judge always prefers blind label "A"; the JudgeAgent randomises which real
answer is labelled A, so we drive the seed to assert both mappings.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("METAPHOR_MOCK", "1")

from metaphor_machine.agents.judge import JudgeAgent
from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import (
    JUDGE_CRITERIA,
    ComparisonResult,
    JudgeVerdict,
    ProblemSpec,
    Solution,
)


def _problem() -> ProblemSpec:
    return ProblemSpec(
        raw_user_text="Our 4-person team has 12 projects and keeps missing deadlines.",
        summary="Small team, too many parallel projects, slipping deadlines.",
    )


# ---------------------------------------------------------------------------
# Seeds: find one that puts the metaphor answer as A, and one as B, so the
# tests are robust regardless of the RNG implementation.
# ---------------------------------------------------------------------------
def _seed_for(order: str) -> int:
    import random

    for s in range(100):
        metaphor_first = random.Random(s).random() < 0.5
        if (order == "metaphor_first") == metaphor_first:
            return s
    raise AssertionError("no seed found (should be impossible)")


# ---------------------------------------------------------------------------
# Agent-level
# ---------------------------------------------------------------------------
def test_judge_returns_comparison_result():
    agent = JudgeAgent()
    res = agent.run(_problem(), "metaphor answer", "baseline answer", seed=0)
    assert isinstance(res, ComparisonResult)
    assert res.winner in ("metaphor", "baseline", "tie")
    assert res.order in ("metaphor_first", "baseline_first")


def test_judge_criteria_winners_cover_all_criteria():
    agent = JudgeAgent()
    res = agent.run(_problem(), "m", "b", seed=0)
    assert set(res.criteria_winners) == set(JUDGE_CRITERIA)
    for v in res.criteria_winners.values():
        assert v in ("metaphor", "baseline", "tie")


def test_deanonymise_maps_A_to_correct_side():
    """Mock always picks 'A'. When metaphor is shown first, winner==metaphor;
    when baseline is shown first, the same 'A' means baseline."""
    agent = JudgeAgent()

    res_mfirst = agent.run(_problem(), "m", "b", seed=_seed_for("metaphor_first"))
    assert res_mfirst.order == "metaphor_first"
    assert res_mfirst.winner == "metaphor"

    res_bfirst = agent.run(_problem(), "m", "b", seed=_seed_for("baseline_first"))
    assert res_bfirst.order == "baseline_first"
    assert res_bfirst.winner == "baseline"


def test_deanonymise_tie_passthrough():
    verdict = JudgeVerdict(winner="tie", criteria=[], reasoning="even")
    out = JudgeAgent._deanonymise(verdict, metaphor_first=True)
    assert out.winner == "tie"


def test_deanonymise_b_flips_with_order():
    verdict = JudgeVerdict(winner="B", criteria=[], reasoning="")
    assert JudgeAgent._deanonymise(verdict, metaphor_first=True).winner == "baseline"
    assert JudgeAgent._deanonymise(verdict, metaphor_first=False).winner == "metaphor"


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------
def test_pipeline_run_judge_requires_translator_first():
    pipe = Pipeline()
    pipe.run_definer("a team with too much work")
    with pytest.raises(RuntimeError):
        pipe.run_judge()


def test_pipeline_run_judge_end_to_end():
    pipe = Pipeline()
    pipe.run_definer("a team with too much work")
    pipe.session.solutions = [
        Solution(
            metaphor_idea="drop anchor",
            original_domain_translation="Time-box the top two projects for two days.",
            confidence=0.7,
        )
    ]
    res = pipe.run_judge(baseline_text="Just try to focus more and prioritise.")
    assert isinstance(res, ComparisonResult)
    assert res.winner in ("metaphor", "baseline", "tie")


def test_format_solutions_for_judge_is_numbered_and_original_domain_only():
    sols = [
        Solution(metaphor_idea="X", original_domain_translation="First idea.", confidence=0.5),
        Solution(metaphor_idea="Y", original_domain_translation="Second idea.", confidence=0.5),
    ]
    text = Pipeline.format_solutions_for_judge(sols)
    assert "1. First idea." in text
    assert "2. Second idea." in text
    # must not leak metaphor scaffolding into the judged answer
    assert "X" not in text and "Y" not in text
