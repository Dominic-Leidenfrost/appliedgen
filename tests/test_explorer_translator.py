"""Explorer + Translator agent tests — smoke + schema validity.

All tests run in mock mode (METAPHOR_MOCK=1).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("METAPHOR_MOCK", "1")

from metaphor_machine.agents.explorer import ExplorerAgent
from metaphor_machine.agents.translator import TranslatorAgent
from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import Mapping, MetaphorSpec, Move, ProblemSpec, Solution
from metaphor_machine.storage.markdown_store import MarkdownStore


# ---------------------------------------------------------------------------
# Fixtures
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


@pytest.fixture
def pirate_metaphor() -> MetaphorSpec:
    return MetaphorSpec(
        domain="pirate_adventure",
        domain_intro="A crew sails contested islands for merchant guilds.",
        mappings=[
            Mapping(original="engineer", metaphor="crew member", fidelity=0.8,
                    leak="crew fungible; engineers are not"),
            Mapping(original="project", metaphor="island", fidelity=0.75, leak="islands sequential"),
            Mapping(original="deadline", metaphor="guild meeting", fidelity=0.85,
                    leak="meetings are binary"),
            Mapping(original="quality", metaphor="hull rot", fidelity=0.7,
                    leak="rot invisible until catastrophic"),
        ],
        invariants_preserved=["scarcity forces choices"],
        invariants_broken=["parallel execution impossible on single ship"],
    )


@pytest.fixture
def one_move() -> Move:
    return Move(
        actor="Navigator Priya",
        action="Drops anchor at Westport for two tides.",
        consequence="Hull scraped; ship can sail at full speed again.",
        obstacle="Guild skiff arrives demanding attendance within three days.",
    )


# ---------------------------------------------------------------------------
# ExplorerAgent
# ---------------------------------------------------------------------------

def test_explorer_smoke(pirate_metaphor):
    agent = ExplorerAgent()
    move = agent.run(metaphor=pirate_metaphor, history=[], directive="Repair the hull.")
    assert isinstance(move, Move)


def test_explorer_returns_move_with_obstacle(pirate_metaphor):
    agent = ExplorerAgent()
    move = agent.run(metaphor=pirate_metaphor, history=[], directive="Do something.")
    assert move.obstacle is not None and len(move.obstacle) > 0


def test_explorer_move_schema_valid(pirate_metaphor):
    agent = ExplorerAgent()
    move = agent.run(metaphor=pirate_metaphor, history=[], directive="Advance the plot.")
    raw = move.model_dump()
    Move.model_validate(raw)


def test_explorer_with_history(pirate_metaphor, one_move):
    agent = ExplorerAgent()
    move = agent.run(
        metaphor=pirate_metaphor,
        history=[one_move],
        directive="What happens next?",
    )
    assert isinstance(move, Move)


def test_explorer_validate_missing_obstacle(pirate_metaphor):
    agent = ExplorerAgent()
    bad_move = Move(actor="crew member", action="sail", consequence="arrive", obstacle=None)
    complaints = agent._validate(bad_move, pirate_metaphor)
    assert any("obstacle" in c for c in complaints)


def test_explorer_validate_forbidden_word(pirate_metaphor):
    agent = ExplorerAgent()
    bad_move = Move(
        actor="crew member",
        action="collaborate with the rival crew",
        consequence="synergy achieved",
        obstacle="weather",
    )
    complaints = agent._validate(bad_move, pirate_metaphor)
    assert any("forbidden" in c for c in complaints)


# ---------------------------------------------------------------------------
# TranslatorAgent
# ---------------------------------------------------------------------------

def test_translator_smoke(minimal_problem, pirate_metaphor, one_move):
    agent = TranslatorAgent()
    solutions = agent.run(problem=minimal_problem, metaphor=pirate_metaphor, moves=[one_move])
    assert isinstance(solutions, list)
    assert len(solutions) >= 1


def test_translator_returns_solution_instances(minimal_problem, pirate_metaphor, one_move):
    agent = TranslatorAgent()
    solutions = agent.run(problem=minimal_problem, metaphor=pirate_metaphor, moves=[one_move])
    for s in solutions:
        assert isinstance(s, Solution)


def test_translator_solution_schema_valid(minimal_problem, pirate_metaphor, one_move):
    agent = TranslatorAgent()
    solutions = agent.run(problem=minimal_problem, metaphor=pirate_metaphor, moves=[one_move])
    for s in solutions:
        Solution.model_validate(s.model_dump())


def test_translator_empty_moves(minimal_problem, pirate_metaphor):
    agent = TranslatorAgent()
    solutions = agent.run(problem=minimal_problem, metaphor=pirate_metaphor, moves=[])
    assert solutions == []


# ---------------------------------------------------------------------------
# Pipeline integration (Explorer + Translator)
# ---------------------------------------------------------------------------

def test_pipeline_explorer_turn(minimal_problem, pirate_metaphor):
    pl = Pipeline()
    pl.session.problem = minimal_problem
    pl.session.chosen_metaphor = pirate_metaphor
    move = pl.run_explorer_turn("Repair the hull.")
    assert isinstance(move, Move)
    assert len(pl.session.moves) == 1


def test_pipeline_moves_accumulate(minimal_problem, pirate_metaphor):
    pl = Pipeline()
    pl.session.problem = minimal_problem
    pl.session.chosen_metaphor = pirate_metaphor
    pl.run_explorer_turn("First move")
    pl.run_explorer_turn("Second move")
    assert len(pl.session.moves) == 2


def test_pipeline_translator(minimal_problem, pirate_metaphor, one_move):
    pl = Pipeline()
    pl.session.problem = minimal_problem
    pl.session.chosen_metaphor = pirate_metaphor
    pl.session.moves = [one_move]
    solutions = pl.run_translator()
    assert isinstance(solutions, list)
    assert pl.session.solutions == solutions


def test_pipeline_translator_requires_moves(minimal_problem, pirate_metaphor):
    pl = Pipeline()
    pl.session.problem = minimal_problem
    pl.session.chosen_metaphor = pirate_metaphor
    with pytest.raises(RuntimeError, match="No moves"):
        pl.run_translator()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def test_markdown_store_creates_folder(minimal_problem, pirate_metaphor, one_move):
    with tempfile.TemporaryDirectory() as tmp:
        pl = Pipeline()
        pl.session.problem = minimal_problem
        pl.session.metaphor_candidates = [pirate_metaphor]
        pl.session.chosen_metaphor = pirate_metaphor
        pl.session.moves = [one_move]
        store = MarkdownStore(base_dir=tmp)
        folder = store.save(pl.session, slug="test")
        assert folder.exists()


def test_markdown_store_writes_json_sidecar(minimal_problem):
    with tempfile.TemporaryDirectory() as tmp:
        pl = Pipeline()
        pl.session.problem = minimal_problem
        store = MarkdownStore(base_dir=tmp)
        folder = store.save(pl.session, slug="test")
        assert (folder / "problem.json").exists()
        assert (folder / "session.json").exists()


def test_markdown_store_writes_md_files(minimal_problem, pirate_metaphor, one_move):
    with tempfile.TemporaryDirectory() as tmp:
        pl = Pipeline()
        pl.session.problem = minimal_problem
        pl.session.metaphor_candidates = [pirate_metaphor]
        pl.session.moves = [one_move]
        store = MarkdownStore(base_dir=tmp)
        folder = store.save(pl.session, slug="test")
        assert (folder / "problem.md").exists()
        assert (folder / "metaphors.md").exists()
        assert (folder / "transcript.md").exists()
