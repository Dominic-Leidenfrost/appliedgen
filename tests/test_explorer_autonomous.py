"""Tests for the autonomous Explorer behaviour.

The Explorer is the generator, not a reactor. These tests verify:
- It runs without any user input (None directive).
- The force_different flag is plumbed through to the prompt.
- undo_last_move pops the most recent move and preserves the rest.
- The prompt actually instructs the LLM to vary strategy when force_different.
"""

from __future__ import annotations

import pytest

from metaphor_machine.agents.explorer import ExplorerAgent
from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import MetaphorSpec, Move


@pytest.fixture(autouse=True)
def enable_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METAPHOR_MOCK", "1")


@pytest.fixture
def pirate_metaphor() -> MetaphorSpec:
    """Minimal MetaphorSpec good enough to exercise the Explorer prompt."""
    return MetaphorSpec(
        domain="pirate_adventure",
        domain_intro="A small crew sails contested waters.",
        mappings=[
            {"original": "team", "metaphor": "Navigator Priya", "fidelity": 0.8, "leak": None},
            {"original": "deadline", "metaphor": "Westport harbour", "fidelity": 0.7, "leak": None},
        ],
    )


class TestAutonomousExplorer:
    def test_runs_without_directive(self, pirate_metaphor: MetaphorSpec) -> None:
        """No user input required — Explorer generates on its own."""
        agent = ExplorerAgent()
        move = agent.run(metaphor=pirate_metaphor, history=[])
        assert isinstance(move, Move)
        assert move.actor and move.action and move.consequence

    def test_directive_accepted_but_optional(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        agent = ExplorerAgent()
        # None
        move_a = agent.run(metaphor=pirate_metaphor, history=[], directive=None)
        # Empty string
        move_b = agent.run(metaphor=pirate_metaphor, history=[], directive="")
        # Actual steering
        move_c = agent.run(
            metaphor=pirate_metaphor, history=[], directive="focus on the navigator"
        )
        for m in (move_a, move_b, move_c):
            assert isinstance(m, Move)


class TestForceDifferentInstruction:
    """The force_different flag must change the prompt sent to the LLM."""

    def test_first_move_prompt_has_no_diversity_clause(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        msgs = ExplorerAgent._build_messages(
            pirate_metaphor, history=[], directive=None, force_different=False
        )
        user_msg = msgs[-1]["content"]
        assert "FIRST move" in user_msg
        assert "structurally DIFFERENT" not in user_msg

    def test_force_different_adds_diversity_instruction(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        prior = Move(
            actor="Captain Reyes",
            action="orders a change of course",
            consequence="crew gripes",
            obstacle="storm",
        )
        msgs = ExplorerAgent._build_messages(
            pirate_metaphor, history=[prior], directive=None, force_different=True
        )
        user_msg = msgs[-1]["content"]
        assert "structurally DIFFERENT" in user_msg

    def test_directive_appears_in_prompt(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        msgs = ExplorerAgent._build_messages(
            pirate_metaphor,
            history=[],
            directive="focus on the quiet druid",
            force_different=False,
        )
        user_msg = msgs[-1]["content"]
        assert "focus on the quiet druid" in user_msg


class TestPipelineExplorerControls:
    def test_run_explorer_turn_appends_to_session(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        pl = Pipeline()
        pl.session.chosen_metaphor = pirate_metaphor
        assert len(pl.session.moves) == 0
        pl.run_explorer_turn()  # no directive needed
        assert len(pl.session.moves) == 1

    def test_undo_last_move_pops_one(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        pl = Pipeline()
        pl.session.chosen_metaphor = pirate_metaphor
        pl.run_explorer_turn()
        pl.run_explorer_turn()
        assert len(pl.session.moves) == 2
        popped = pl.undo_last_move()
        assert popped is not None
        assert len(pl.session.moves) == 1

    def test_undo_on_empty_history_returns_none(self) -> None:
        pl = Pipeline()
        assert pl.undo_last_move() is None

    def test_force_different_kwarg_propagates(
        self, pirate_metaphor: MetaphorSpec
    ) -> None:
        """Pipeline.run_explorer_turn(force_different=True) must reach the
        agent — verify by intercepting agent.run."""
        pl = Pipeline()
        pl.session.chosen_metaphor = pirate_metaphor
        captured: dict = {}
        real_run = pl.explorer.run

        def spy(**kwargs):
            captured.update(kwargs)
            return real_run(**kwargs)

        pl.explorer.run = spy  # type: ignore[assignment]
        pl.run_explorer_turn(directive="x", force_different=True)
        assert captured["force_different"] is True
        assert captured["directive"] == "x"
