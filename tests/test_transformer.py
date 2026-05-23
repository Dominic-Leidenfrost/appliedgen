"""Transformer agent tests — smoke + schema validity.

All tests run in mock mode (METAPHOR_MOCK=1) so no API key is needed.
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("METAPHOR_MOCK", "1")

from metaphor_machine.agents.transformer import TransformerAgent
from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import MetaphorSpec, ProblemSpec
from metaphor_machine.prompts.check import find_forbidden
from metaphor_machine.prompts.domains import load_all, pick_diverse


# ---------------------------------------------------------------------------
# Domain loader
# ---------------------------------------------------------------------------

def test_load_all_domains_returns_seeds():
    seeds = load_all()
    assert len(seeds) >= 8, "Expected at least 8 seed domains"


def test_pick_diverse_returns_n():
    for n in (1, 2, 3):
        seeds = pick_diverse(n=n)
        assert len(seeds) == n


def test_pick_diverse_names_are_distinct():
    seeds = pick_diverse(n=3)
    names = [s.name for s in seeds]
    assert len(set(names)) == len(names), "pick_diverse returned duplicate domains"


def test_domain_seed_as_style_hint_contains_name():
    seeds = load_all()
    hint = seeds[0].as_style_hint()
    assert seeds[0].display in hint


# ---------------------------------------------------------------------------
# Forbidden words
# ---------------------------------------------------------------------------

def test_find_forbidden_detects_weasel_words():
    hits = find_forbidden("We need to collaborate and leverage synergy.")
    assert "collaborate" in hits
    assert "synergy" in hits
    assert "leverage" in hits


def test_find_forbidden_clean_text():
    hits = find_forbidden("The captain storms the harbour at dawn.")
    assert hits == []


def test_find_forbidden_case_insensitive():
    hits = find_forbidden("STAKEHOLDER meeting tomorrow.")
    assert "stakeholder" in hits


# ---------------------------------------------------------------------------
# TransformerAgent (mock)
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_problem() -> ProblemSpec:
    return ProblemSpec(
        raw_user_text="Team overloaded with projects",
        summary="Resource-constrained multi-project team",
        entities=[],
        relations=[],
        constraints=["fixed headcount"],
        goals=["ship on time"],
        tensions=["speed vs. quality"],
        unknowns=[],
    )


def test_transformer_smoke(minimal_problem):
    agent = TransformerAgent(style_hint="pirate adventure")
    result = agent.run(minimal_problem)
    assert isinstance(result, MetaphorSpec)


def test_transformer_mock_has_four_mappings(minimal_problem):
    agent = TransformerAgent()
    result = agent.run(minimal_problem)
    assert len(result.mappings) >= 4


def test_transformer_mock_schema_valid(minimal_problem):
    agent = TransformerAgent()
    result = agent.run(minimal_problem)
    # Round-trip through model_dump -> model_validate
    raw = result.model_dump()
    reloaded = MetaphorSpec.model_validate(raw)
    assert reloaded.domain == result.domain


# ---------------------------------------------------------------------------
# Pipeline.run_transformer (mock, parallel)
# ---------------------------------------------------------------------------

def test_pipeline_run_transformer_returns_list(minimal_problem):
    pipeline = Pipeline()
    pipeline.session.problem = minimal_problem
    candidates = pipeline.run_transformer(n=3)
    assert isinstance(candidates, list)
    assert len(candidates) >= 1
    for c in candidates:
        assert isinstance(c, MetaphorSpec)


def test_pipeline_stores_candidates(minimal_problem):
    pipeline = Pipeline()
    pipeline.session.problem = minimal_problem
    pipeline.run_transformer(n=2)
    assert len(pipeline.session.metaphor_candidates) >= 1
