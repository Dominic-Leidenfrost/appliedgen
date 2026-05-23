"""End-to-end pipeline tests using the seed problem fixtures.

These run against the mock LLM (METAPHOR_MOCK=1) so they're fast and don't
need an API key. They exercise the full call chain:
    user_text -> Pipeline -> DefinerAgent -> LLMClient -> Pydantic -> Session
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import ProblemSpec

FIXTURES = Path(__file__).parent / "fixtures" / "problems.yaml"


@pytest.fixture(autouse=True)
def enable_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METAPHOR_MOCK", "1")


def _load_problems() -> list[dict[str, str]]:
    return yaml.safe_load(FIXTURES.read_text())["problems"]


@pytest.mark.parametrize(
    "problem",
    _load_problems(),
    ids=lambda p: p["id"],
)
def test_definer_runs_for_each_seed_problem(problem: dict[str, str]) -> None:
    """The Definer must produce a schema-valid ProblemSpec for every seed."""
    pipeline = Pipeline()
    spec = pipeline.run_definer(problem["user_text"])
    assert isinstance(spec, ProblemSpec)
    # Pipeline state contract
    assert pipeline.session.problem is spec
    assert pipeline.session.raw_input == problem["user_text"]
    # Schema validation guarantees
    assert spec.summary
    assert spec.entities, "Definer must extract at least one entity"


def test_fixtures_cover_three_categories() -> None:
    """We want diversity in seed problems for the eval (PLAN.md §8)."""
    cats = {p["category"] for p in _load_problems()}
    assert cats == {"mechanical", "organizational", "social"}


def test_fixture_user_texts_are_substantive() -> None:
    """Seed problems should be detailed enough to actually exercise extraction."""
    for p in _load_problems():
        assert len(p["user_text"].split()) >= 15, (
            f"Problem {p['id']} is too short to test the Definer meaningfully."
        )
