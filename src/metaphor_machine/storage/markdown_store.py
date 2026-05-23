"""Persist sessions as markdown (for humans) + JSON sidecar (for replay).

See PLAN.md — answer to "Wie wird das gespeichert?".
One folder per run: data/runs/<timestamp>-<slug>/
  problem.md / problem.json
  metaphors.md / metaphors.json
  transcript.md / moves.json
  solutions.md / solutions.json
  session.json   ← full session blob
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from ..core.pipeline import Session
from ..core.schemas import MetaphorSpec, Move, ProblemSpec, Solution


class MarkdownStore:
    def __init__(self, base_dir: str | os.PathLike[str] | None = None) -> None:
        self.base = Path(base_dir or os.getenv("METAPHOR_DATA_DIR", "./data/runs"))
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session, slug: str = "session") -> Path:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = self.base / f"{ts}-{slug}"
        folder.mkdir(parents=True, exist_ok=True)

        if session.problem:
            (folder / "problem.json").write_text(session.problem.model_dump_json(indent=2))
            (folder / "problem.md").write_text(_render_problem(session.problem))

        if session.metaphor_candidates:
            (folder / "metaphors.json").write_text(
                json.dumps([m.model_dump() for m in session.metaphor_candidates], indent=2)
            )
            (folder / "metaphors.md").write_text(
                _render_metaphors(session.metaphor_candidates, session.chosen_metaphor)
            )

        if session.moves:
            (folder / "moves.json").write_text(
                json.dumps([m.model_dump() for m in session.moves], indent=2)
            )
            (folder / "transcript.md").write_text(
                _render_transcript(session.moves, session.chosen_metaphor)
            )

        if session.solutions:
            (folder / "solutions.json").write_text(
                json.dumps([s.model_dump() for s in session.solutions], indent=2)
            )
            (folder / "solutions.md").write_text(_render_solutions(session.solutions))

        # Full session blob for programmatic replay
        (folder / "session.json").write_text(
            json.dumps(
                {
                    "raw_input": session.raw_input,
                    "problem": session.problem.model_dump() if session.problem else None,
                    "metaphor_candidates": [m.model_dump() for m in session.metaphor_candidates],
                    "chosen_metaphor": session.chosen_metaphor.model_dump()
                    if session.chosen_metaphor
                    else None,
                    "moves": [m.model_dump() for m in session.moves],
                    "solutions": [s.model_dump() for s in session.solutions],
                },
                indent=2,
            )
        )

        return folder


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------


def _render_problem(p: ProblemSpec) -> str:
    lines = [
        f"# Problem\n",
        f"**Summary:** {p.summary}\n",
        f"**Original input:** {p.raw_user_text}\n",
        "## Entities\n",
    ]
    for e in p.entities:
        attrs = ", ".join(e.attributes) or "_none_"
        lines.append(f"- **{e.name}** ({e.role}) — {attrs}")
    lines += ["", "## Relations\n"]
    for r in p.relations:
        lines.append(f"- `{r.source}` --{r.kind}--> `{r.target}` (strength {r.strength:.2f})")
    lines += ["", "## Constraints\n"]
    for c in p.constraints:
        lines.append(f"- {c}")
    lines += ["", "## Goals\n"]
    for g in p.goals:
        lines.append(f"- {g}")
    lines += ["", "## Tensions\n"]
    for t in p.tensions:
        lines.append(f"- ⚡ {t}")
    if p.unknowns:
        lines += ["", "## Open questions\n"]
        for u in p.unknowns:
            lines.append(f"- ❓ {u}")
    return "\n".join(lines) + "\n"


def _render_metaphors(candidates: list[MetaphorSpec], chosen: MetaphorSpec | None) -> str:
    lines = ["# Metaphor candidates\n"]
    for m in candidates:
        marker = " ✅ (chosen)" if chosen and chosen.domain == m.domain else ""
        lines += [
            f"## {m.domain.replace('_', ' ').title()}{marker}\n",
            m.domain_intro,
            "",
            "### Mappings\n",
            "| Original | Metaphor | Fidelity | Leak |",
            "|---|---|---|---|",
        ]
        for mp in m.mappings:
            leak = mp.leak or "_none_"
            lines.append(f"| {mp.original} | {mp.metaphor} | {mp.fidelity:.2f} | {leak} |")
        if m.invariants_preserved:
            lines += ["", "### Preserved invariants\n"]
            for inv in m.invariants_preserved:
                lines.append(f"- ✔ {inv}")
        if m.invariants_broken:
            lines += ["", "### Broken invariants\n"]
            for inv in m.invariants_broken:
                lines.append(f"- ✖ {inv}")
        lines.append("")
    return "\n".join(lines)


def _render_transcript(moves: list[Move], metaphor: MetaphorSpec | None) -> str:
    domain = metaphor.domain.replace("_", " ").title() if metaphor else "unknown"
    lines = [f"# Explorer transcript — {domain}\n"]
    for i, m in enumerate(moves, 1):
        lines += [
            f"## Move {i}: {m.actor}\n",
            f"**Action:** {m.action}\n",
            f"**Consequence:** {m.consequence}\n",
            f"**Obstacle:** {m.obstacle or '_(none recorded)_'}\n",
        ]
    return "\n".join(lines)


def _render_solutions(solutions: list[Solution]) -> str:
    lines = ["# Solutions\n"]
    for i, s in enumerate(solutions, 1):
        lines += [
            f"## Solution {i} (confidence {s.confidence:.0%})\n",
            f"**Metaphor idea:** {s.metaphor_idea}\n",
            f"**Translation:** {s.original_domain_translation}\n",
        ]
        if s.caveats:
            lines += ["**Caveats:**\n"]
            for c in s.caveats:
                lines.append(f"- ⚠️ {c}")
        lines.append("")
    return "\n".join(lines)
