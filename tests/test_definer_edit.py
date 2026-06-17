"""Tests for user-correctable Definer output (Pipeline.update_problem).

Mock mode so no API key needed.
"""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("METAPHOR_MOCK", "1")

from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import Entity, ProblemSpec, Relation


def _spec(summary: str = "original summary") -> ProblemSpec:
    return ProblemSpec(
        raw_user_text="raw",
        summary=summary,
        entities=[Entity(name="a", role="actor")],
    )


def test_update_problem_replaces_spec():
    pipe = Pipeline()
    pipe.run_definer("some problem")
    edited = _spec("corrected summary")
    out = pipe.update_problem(edited)
    assert out.summary == "corrected summary"
    assert pipe.session.problem is edited


def test_update_problem_accepts_dict_and_validates():
    pipe = Pipeline()
    out = pipe.update_problem(
        {"raw_user_text": "r", "summary": "from dict", "entities": []}
    )
    assert isinstance(out, ProblemSpec)
    assert out.summary == "from dict"


def test_update_problem_rejects_invalid():
    pipe = Pipeline()
    with pytest.raises(ValidationError):
        # strength out of [0,1] range -> pydantic ValidationError
        pipe.update_problem(
            {
                "raw_user_text": "r",
                "summary": "s",
                "relations": [
                    {"source": "a", "target": "b", "kind": "x", "strength": 5.0}
                ],
            }
        )


def test_update_problem_clears_stale_downstream():
    """Editing the problem must drop metaphors/moves/solutions built from the
    OLD problem, so two problem definitions never mix."""
    pipe = Pipeline()
    pipe.run_definer("team overloaded")
    pipe.run_transformer(n=2)
    pipe.session.chosen_metaphor = pipe.session.metaphor_candidates[0]
    pipe.run_explorer_turn()
    assert pipe.session.metaphor_candidates and pipe.session.moves

    pipe.update_problem(_spec("totally different problem now"))

    assert pipe.session.metaphor_candidates == []
    assert pipe.session.chosen_metaphor is None
    assert pipe.session.moves == []
    assert pipe.session.solutions == []


def test_update_problem_without_downstream_keeps_things_empty():
    pipe = Pipeline()
    pipe.run_definer("a problem")
    # no transformer run yet
    pipe.update_problem(_spec("edited"))
    assert pipe.session.problem.summary == "edited"
    assert pipe.session.metaphor_candidates == []


def test_edited_problem_feeds_transformer():
    """After a correction the corrected spec is what the Transformer sees."""
    pipe = Pipeline()
    pipe.run_definer("vague")
    edited = ProblemSpec(
        raw_user_text="vague",
        summary="sharp corrected problem",
        entities=[Entity(name="server", role="actor")],
        relations=[Relation(source="server", target="server", kind="loops", strength=0.5)],
    )
    pipe.update_problem(edited)
    assert pipe.session.problem.summary == "sharp corrected problem"
    # transformer runs off the corrected problem without error
    cands = pipe.run_transformer(n=1)
    assert len(cands) == 1
