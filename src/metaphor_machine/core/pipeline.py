"""Orchestrator that wires the four agents together.

This is intentionally thin: agents are stateless, the pipeline owns the session
state and decides what runs when. See PLAN.md §2 for the architecture diagram.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from ..agents.definer import DefinerAgent
from ..agents.explorer import ExplorerAgent
from ..agents.transformer import TransformerAgent
from ..agents.translator import TranslatorAgent
from ..llm import LLMConfig
from ..prompts.domains import DomainSeed, pick_diverse
from ..prompts.language import (
    Language,
    persist_language,
    resolve_language,
)
from .schemas import MetaphorSpec, Move, ProblemSpec, Solution


# Per-agent default temperatures (PLAN.md §2 table).
_AGENT_TEMP = {
    "definer": 0.2,
    "transformer": 0.9,
    "explorer": 0.7,
    "translator": 0.3,
}


# ---------------------------------------------------------------------------
# Persisted model choice
# ---------------------------------------------------------------------------
#
# Streamlit recreates the Pipeline on every page reload, which would reset
# the user's model choice to the env default every time. We persist the most
# recent choice to a tiny file under data/cache/ so reloads pick it back up.
#
# This is intentionally NOT in storage/markdown_store.py — that module handles
# session output (problem.md, solutions.md, ...). The model-choice file is
# *machine config*, not session content. Keeping them separate so wiping
# data/runs/ never touches the saved model preference.

_MODEL_CACHE_FILE = Path(
    os.getenv("METAPHOR_CACHE_DIR", "./data/cache")
) / "active_model.txt"


def _load_persisted_model() -> str | None:
    """Return the last set_model() value, or None if missing/unreadable."""
    try:
        text = _MODEL_CACHE_FILE.read_text().strip()
        # Sanity check: must look like a LiteLLM model string ("provider/model")
        if text and "/" in text and len(text) < 200:
            return text
    except (OSError, FileNotFoundError):
        pass
    return None


def _persist_model(model: str) -> None:
    """Best-effort write — silently ignore disk/perm errors."""
    try:
        _MODEL_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MODEL_CACHE_FILE.write_text(model)
    except OSError:
        pass


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
    """Orchestrator. All four agents wired up as of Sprint 3.

    The `model` attribute is the LiteLLM model string used for every agent
    call. It can be changed at runtime with `set_model()` — already-constructed
    agents are dropped so the next access rebuilds them with the new model.
    Session state (problem, metaphors, moves, solutions) is preserved.
    """

    def __init__(
        self,
        session: Session | None = None,
        model: str | None = None,
        language: Language | None = None,
    ) -> None:
        self.session = session or Session()
        self.model = (
            model
            or _load_persisted_model()
            or os.getenv("METAPHOR_DEFAULT_MODEL", "anthropic/claude-sonnet-4-6")
        )
        self.language: Language = resolve_language(language)
        self._definer: DefinerAgent | None = None
        self._explorer: ExplorerAgent | None = None
        self._translator: TranslatorAgent | None = None

    def set_language(self, language: Language) -> None:
        """Switch output language for future agent calls.

        Drops cached agents so they're rebuilt with the new language clause.
        Session state (already-generated content) is preserved — only NEW
        agent output will be in the new language. Persists across reloads.
        """
        if language == self.language:
            return
        self.language = language
        self._definer = None
        self._explorer = None
        self._translator = None
        persist_language(language)

    def set_model(self, model: str) -> None:
        """Switch the model used for future agent calls.

        Drops cached agent instances so the next call rebuilds them with the
        new model. Does NOT touch session state — problem, metaphors, moves
        and solutions already collected are preserved. Persists the choice
        to disk so it survives page reloads / process restarts.
        """
        if model == self.model:
            return
        self.model = model
        self._definer = None
        self._explorer = None
        self._translator = None
        _persist_model(model)

    def _config_for(self, agent_name: str) -> LLMConfig:
        return LLMConfig(model=self.model, temperature=_AGENT_TEMP[agent_name])

    @property
    def definer(self) -> DefinerAgent:
        if self._definer is None:
            self._definer = DefinerAgent(
                config=self._config_for("definer"), language=self.language
            )
        return self._definer

    @property
    def explorer(self) -> ExplorerAgent:
        if self._explorer is None:
            self._explorer = ExplorerAgent(
                config=self._config_for("explorer"), language=self.language
            )
        return self._explorer

    @property
    def translator(self) -> TranslatorAgent:
        if self._translator is None:
            self._translator = TranslatorAgent(
                config=self._config_for("translator"), language=self.language
            )
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

        transformer_config = self._config_for("transformer")
        transformer_language = self.language

        def _run_one(seed: DomainSeed) -> MetaphorSpec:
            agent = TransformerAgent(
                style_hint=seed,
                config=transformer_config,
                language=transformer_language,
            )
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

    # --- step 3: Explorer (autonomous, with optional steering) ---
    def run_explorer_turn(
        self,
        directive: str | None = None,
        force_different: bool = False,
    ) -> Move:
        """Generate the next Move autonomously.

        Args:
            directive: optional user steering text. If None/empty, the
                Explorer picks the next move with full autonomy.
            force_different: ask for a strategy structurally unlike prior
                moves. Wired to the UI's 'Try different angle' button.
        """
        if self.session.chosen_metaphor is None:
            raise RuntimeError("User must pick a metaphor first.")
        move = self.explorer.run(
            metaphor=self.session.chosen_metaphor,
            history=self.session.moves,
            directive=directive,
            force_different=force_different,
        )
        self.session.moves.append(move)
        return move

    def undo_last_move(self) -> Move | None:
        """Pop the most recent Move from the session. Returns the popped Move
        (so the UI can confirm) or None if there was nothing to undo."""
        if self.session.moves:
            return self.session.moves.pop()
        return None

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
