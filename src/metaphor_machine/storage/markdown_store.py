"""Persist sessions as markdown (for humans) + JSON sidecar (for replay).

See PLAN.md — answer to "Wie wird das gespeichert?".
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from ..core.pipeline import Session


class MarkdownStore:
    def __init__(self, base_dir: str | os.PathLike[str] | None = None) -> None:
        self.base = Path(base_dir or os.getenv("METAPHOR_DATA_DIR", "./data/runs"))
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session, slug: str = "session") -> Path:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = self.base / f"{ts}-{slug}"
        folder.mkdir(parents=True, exist_ok=True)

        # JSON sidecar — full state, replayable
        if session.problem is not None:
            (folder / "problem.json").write_text(session.problem.model_dump_json(indent=2))
        if session.metaphor_candidates:
            (folder / "metaphors.json").write_text(
                json.dumps([m.model_dump() for m in session.metaphor_candidates], indent=2)
            )
        if session.moves:
            (folder / "moves.json").write_text(
                json.dumps([m.model_dump() for m in session.moves], indent=2)
            )
        if session.solutions:
            (folder / "solutions.json").write_text(
                json.dumps([s.model_dump() for s in session.solutions], indent=2)
            )

        # TODO(sprint-3): render human-readable .md views from the same data.
        return folder
