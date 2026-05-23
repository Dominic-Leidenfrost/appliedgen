"""Orchestrator that wires the four agents together.

This is intentionally thin: agents are stateless, the pipeline owns the session
state and decides what runs when. See PLAN.md §2 for the architecture diagram.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from ..agents.definer import DefinerAgent
from ..agents.explorer import ExplorerAgent
from ..agents.transformer import TransformerAgent
from ..agents.translator import TranslatorAgent
from ..prompts.domains import DomainSeed, pick_diverse
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
    """Orchestrator. All four agents wired up as of Sprint 3."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or Session()
        self._definer: DefinerAgent | None = None
        self._explorer: ExplorerAgent | None = None
        self._translator: TranslatorAgent | None = None

    @property
    def definer(self) -> DefinerAgent:
        if self._definer is None:
            self._definer = DefinerAgent()
        return self._definer

    @property
    def explorer(self) -> ExplorerAgent:
        if self._explorer is None:
            self._explorer = ExplorerAgent()
        return self._explorer

    @property
    def translator(self) -> TranslatorAgent:
        if self._translator is None:
            self._translator = TranslatorAgent()
        return self._translator

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

        seeds: list[DomainSeed] = pick_diverse(n=n)
        # If no seed domains found (e.g. wrong working dir in tests), run without hints.
        if not seeds:
            from ..prompts.domains import DomainSeed as _DS
            seeds = [_DS(name=f"domain_{i}", display="", description="", vocabulary=[], archetypal_entities={}, typical_relations=[]) for i in range(n)]
        problem = self.session.problem

        def _run_one(seed: DomainSeed) -> MetaphorSpec:
            agent = TransformerAgent(style_hint=seed)
            return agent.run(problem)

        results: list[MetaphorSpec] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = {pool.submit(_run_one, seed): seed for seed in seeds}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors.append(f"{futures[future].name}: {exc}")

        if not results:
            raise RuntimeError(
                f"All {n} Transformer runs failed:\n" + "\n".join(errors)
            )

        # Apply diversity filter so we return the most structurally different ones
        diverse = TransformerAgent._pick_diverse_mappings(results, n=min(n, len(results)))
        self.session.metaphor_candidates = diverse
        return diverse

    # --- step 3: Explorer (interactive loop) ---
    def run_explorer_turn(self, user_message: str) -> Move:
        if self.session.chosen_metaphor is None:
            raise RuntimeError("User must pick a metaphor first.")
        move = self.explorer.run(
            metaphor=self.session.chosen_metaphor,
            history=self.session.moves,
            user_message=user_message,
        )
        self.session.moves.append(move)
        return move

    # --- step 4: Translator ---
    def run_translator(self) -> list[Solution]:
        if not self.session.moves:
            raise RuntimeError("No moves to translate yet.")
        if self.session.problem is None or self.session.chosen_metaphor is None:
            raise RuntimeError("Definer and Explorer must run before Translator.")
        solutions = self.translator.run(
            problem=self.session.problem,
            metaphor=self.session.chosen_metaphor,
            moves=self.session.moves,
        )
        self.session.solutions = solutions
        return solutions

    def run_baseline(self) -> str:
        """Direct LLM answer without metaphor, for comparison panel."""
        if self.session.problem is None:
            raise RuntimeError("Run the Definer first.")
        return self.translator.baseline(self.session.problem)
