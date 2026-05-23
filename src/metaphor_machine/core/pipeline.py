"""Orchestrator that wires the four agents together.

This is intentionally thin: agents are stateless, the pipeline owns the session
state and decides what runs when. See PLAN.md §2 for the architecture diagram.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agents.definer import DefinerAgent
from .schemas import MetaphorSpec, Move, ProblemSpec, Solution


@dataclass
class Session:
    """All state for one user session. Persisted via storage layer."""

    raw_input: str = ""
    problem: ProblemSpec | None = None
    metaphor_candidates: list[MetaphorSpec] = field(default_factory=list)
    chosen_metaphor: MetaphorSpec | None = None
    moves: list[Move] = field(default_factory=list)
    solutions: list[Solution] = field(default_factory=list)


class Pipeline:
    """Orchestrator. Sprint 1: Definer implemented. Other steps stubbed."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or Session()
        # Agents are constructed lazily so importing Pipeline doesn't require
        # any env / API keys to be set yet.
        self._definer: DefinerAgent | None = None

    @property
    def definer(self) -> DefinerAgent:
        if self._definer is None:
            self._definer = DefinerAgent()
        return self._definer

    # --- step 1: Definer ---
    def run_definer(self, user_text: str) -> ProblemSpec:
        self.session.raw_input = user_text
        spec = self.definer.run(user_text)
        self.session.problem = spec
        return spec

    # --- step 2: Transformer (×N parallel) ---
    def run_transformer(self, n: int = 3) -> list[MetaphorSpec]:
        if self.session.problem is None:
            raise RuntimeError("Run the Definer first.")
        # TODO(sprint-2): call TransformerAgent in parallel, deduplicate by diversity
        raise NotImplementedError("Transformer agent — implement in Sprint 2")

    # --- step 3: Explorer (interactive loop) ---
    def run_explorer_turn(self, user_message: str) -> Move:
        if self.session.chosen_metaphor is None:
            raise RuntimeError("User must pick a metaphor first.")
        # TODO(sprint-3): call ExplorerAgent with current moves + user_message
        raise NotImplementedError("Explorer agent — implement in Sprint 3")

    # --- step 4: Translator ---
    def run_translator(self) -> list[Solution]:
        if not self.session.moves:
            raise RuntimeError("No moves to translate yet.")
        # TODO(sprint-3): call TranslatorAgent over each interesting move
        raise NotImplementedError("Translator agent — implement in Sprint 3")
