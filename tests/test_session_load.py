"""Tests for session save → load round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaphor_machine.core.pipeline import Pipeline, Session
from metaphor_machine.core.schemas import MetaphorSpec, Move, ProblemSpec, Solution
from metaphor_machine.storage.markdown_store import (
    MarkdownStore,
    load_session_from_json,
)


def _full_session() -> Session:
    """Build a Session with every field populated, for round-trip coverage."""
    s = Session(raw_input="too many priorities")
    s.problem = ProblemSpec(
        raw_user_text="too many priorities",
        summary="overloaded team",
        entities=[{"name": "team", "role": "actor", "attributes": ["small"]}],  # type: ignore[list-item]
        relations=[
            {"source": "team", "target": "projects", "kind": "buried_under"}  # type: ignore[list-item]
        ],
        constraints=["4 people"],
        goals=["ship the right things"],
        tensions=["speed vs. quality"],
        unknowns=[],
    )
    metaphor = MetaphorSpec(
        domain="pirate_adventure",
        domain_intro="A crew sails contested waters.",
        mappings=[
            {  # type: ignore[list-item]
                "original": "team",
                "metaphor": "crew",
                "fidelity": 0.8,
                "leak": "crew is fungible; team isn't",
            }
        ],
    )
    s.metaphor_candidates = [metaphor]
    s.chosen_metaphor = metaphor
    s.moves = [
        Move(
            actor="Captain Reyes",
            action="drop anchor",
            consequence="hull repaired",
            obstacle="guild skiff arrives",
        )
    ]
    s.solutions = [
        Solution(
            metaphor_idea="drop anchor at one island",
            original_domain_translation="commit to one project for 2 weeks",
            confidence=0.7,
            caveats=["islands are static; projects aren't"],
        )
    ]
    return s


class TestRoundTrip:
    def test_save_then_load_recovers_session(self, tmp_path: Path) -> None:
        store = MarkdownStore(tmp_path)
        original = _full_session()
        folder = store.save(original, slug="test")
        loaded = store.load(folder)

        assert loaded.raw_input == original.raw_input
        assert loaded.problem.summary == original.problem.summary
        assert len(loaded.metaphor_candidates) == 1
        assert loaded.chosen_metaphor.domain == "pirate_adventure"
        assert len(loaded.moves) == 1
        assert loaded.moves[0].actor == "Captain Reyes"
        assert len(loaded.solutions) == 1
        assert loaded.solutions[0].confidence == 0.7

    def test_load_invalid_folder_raises(self, tmp_path: Path) -> None:
        store = MarkdownStore(tmp_path)
        with pytest.raises(FileNotFoundError):
            store.load(tmp_path / "does-not-exist")

    def test_list_sessions_newest_first(self, tmp_path: Path) -> None:
        import time

        store = MarkdownStore(tmp_path)
        store.save(_full_session(), slug="aaa")
        time.sleep(1.05)  # ensure distinct timestamps in folder name
        store.save(_full_session(), slug="bbb")

        listed = store.list_sessions()
        assert len(listed) == 2
        # Newest first → 'bbb' (later timestamp) should be index 0
        assert "bbb" in listed[0].name
        assert "aaa" in listed[1].name

    def test_list_sessions_ignores_folders_without_session_json(
        self, tmp_path: Path
    ) -> None:
        store = MarkdownStore(tmp_path)
        store.save(_full_session(), slug="valid")
        # Create a stray folder
        (tmp_path / "stray-folder").mkdir()

        listed = store.list_sessions()
        assert len(listed) == 1
        assert "valid" in listed[0].name

    def test_load_from_raw_json_string(self) -> None:
        original = _full_session()
        # Serialize to JSON manually (simulates an uploaded file)
        import json as _json
        blob = _json.dumps(
            {
                "raw_input": original.raw_input,
                "problem": original.problem.model_dump(),
                "metaphor_candidates": [m.model_dump() for m in original.metaphor_candidates],
                "chosen_metaphor": original.chosen_metaphor.model_dump(),
                "moves": [m.model_dump() for m in original.moves],
                "solutions": [s.model_dump() for s in original.solutions],
            }
        )
        loaded = load_session_from_json(blob)
        assert loaded.problem.summary == original.problem.summary

    def test_load_from_garbage_raises(self) -> None:
        with pytest.raises(ValueError):
            load_session_from_json("not even json")

    def test_loaded_session_can_drive_pipeline(self, tmp_path: Path) -> None:
        """The loaded session must be usable as the Pipeline's session — i.e.
        you can pick up where you left off, including undo_last_move()."""
        store = MarkdownStore(tmp_path)
        folder = store.save(_full_session(), slug="resumable")
        loaded = store.load(folder)
        pl = Pipeline(session=loaded)

        assert pl.session.problem is not None
        assert len(pl.session.moves) == 1
        popped = pl.undo_last_move()
        assert popped is not None
        assert len(pl.session.moves) == 0
