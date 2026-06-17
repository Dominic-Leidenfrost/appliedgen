"""Orchestrator that wires the four agents together.

This is intentionally thin: agents are stateless, the pipeline owns the session
state and decides what runs when.
"""

from __future__ import annotations

import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from ..agents.definer import DefinerAgent
from ..agents.explorer import ExplorerAgent
from ..agents.judge import JudgeAgent
from ..agents.transformer import TransformerAgent
from ..agents.translator import TranslatorAgent
from ..llm import LLMConfig
from ..logging_config import get_logger
from ..prompts.domains import DomainSeed, pick_diverse
from ..prompts.language import (
    Language,
    persist_language,
    resolve_language,
)
from .schemas import ComparisonResult, MetaphorSpec, Move, ProblemSpec, Solution

log = get_logger(__name__)


# Per-agent default temperatures (PLAN.md §2 table).
_AGENT_TEMP = {
    "definer": 0.2,
    "transformer": 0.9,
    "explorer": 0.7,
    "translator": 0.3,
    # Judge is graded, not generative — keep it deterministic so the eval is
    # reproducible (see agents/judge.py).
    "judge": 0.0,
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
        # Surfaced to UI when a transformer parallel run failed silently.
        self.last_transformer_errors: list[str] = []
        self._definer: DefinerAgent | None = None
        self._explorer: ExplorerAgent | None = None
        self._translator: TranslatorAgent | None = None
        self._judge: JudgeAgent | None = None

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
        self._judge = None
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
        self._judge = None
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

    @property
    def judge(self) -> JudgeAgent:
        if self._judge is None:
            self._judge = JudgeAgent(
                config=self._config_for("judge"), language=self.language
            )
        return self._judge

    # --- step 1: Definer ---
    def run_definer(self, user_text: str) -> ProblemSpec:
        self.session.raw_input = user_text
        log.info(
            "Definer.run start | model=%s lang=%s input_len=%d",
            self.model, self.language, len(user_text),
        )
        t0 = time.perf_counter()
        try:
            spec = self.definer.run(user_text)
        except Exception:
            log.exception("Definer.run failed after %.2fs", time.perf_counter() - t0)
            raise
        dt = time.perf_counter() - t0
        log.info(
            "Definer.run done | %.2fs entities=%d relations=%d tensions=%d",
            dt, len(spec.entities), len(spec.relations), len(spec.tensions),
        )
        self.session.problem = spec
        return spec

    def update_problem(self, problem: ProblemSpec) -> ProblemSpec:
        """Replace the current ProblemSpec with a user-corrected one.

        The Definer is a best-effort extractor: it can mis-read the problem,
        miss an entity, or map a relation differently than the user intends.
        This lets the user fix the structure by hand before it flows into the
        Transformer — the structure the metaphor is built from, so corrections
        here matter more than anywhere else.

        Because the problem is the root of everything downstream, any metaphors,
        moves and solutions already generated from the OLD problem are now stale
        and would silently mix two different problem definitions. We clear them
        and let the user regenerate from the corrected structure.

        Re-validates through Pydantic so a malformed edit can't enter the
        session. Returns the stored spec.
        """
        if not isinstance(problem, ProblemSpec):
            problem = ProblemSpec.model_validate(problem)

        had_downstream = bool(
            self.session.metaphor_candidates
            or self.session.moves
            or self.session.solutions
        )
        self.session.problem = problem
        if had_downstream:
            log.info(
                "update_problem: clearing stale downstream "
                "(metaphors=%d moves=%d solutions=%d)",
                len(self.session.metaphor_candidates),
                len(self.session.moves),
                len(self.session.solutions),
            )
            self.session.metaphor_candidates = []
            self.session.chosen_metaphor = None
            self.session.moves = []
            self.session.solutions = []
            self.last_transformer_errors = []

        log.info(
            "update_problem done | entities=%d relations=%d tensions=%d "
            "downstream_cleared=%s",
            len(problem.entities), len(problem.relations),
            len(problem.tensions), had_downstream,
        )
        return problem

    # --- step 2: Transformer (×N parallel) ---
    def run_transformer(self, n: int = 3, free_domains: bool = False) -> list[MetaphorSpec]:
        """Generate ``n`` metaphor candidates via ``n`` parallel Transformer runs.

        Args:
            n: number of parallel runs / candidates.
            free_domains: if False (default), each run is seeded with a distinct
                domain from the built-in pool (examples/domains/*.yaml) — the
                original behaviour. If True, NO seed is given and each run must
                INVENT its own domain, which can surface domains outside the
                curated pool. Wired to the "Free domains" sidebar toggle.
        """
        if self.session.problem is None:
            raise RuntimeError("Run the Definer first.")
        problem = self.session.problem

        transformer_config = self._config_for("transformer")
        transformer_language = self.language

        # Build the n run units. Each unit has a label (for logging / error
        # reporting) and an optional seed. In free mode there are no seeds.
        if free_domains:
            labels = [f"free_{i + 1}" for i in range(n)]
            seeds_by_label: dict[str, DomainSeed | None] = {lbl: None for lbl in labels}
        else:
            seeds: list[DomainSeed] = pick_diverse(n=n)
            # If no seed domains found (e.g. wrong working dir in tests), run without hints.
            if not seeds:
                from ..prompts.domains import DomainSeed as _DS
                seeds = [
                    _DS(name=f"domain_{i}", display="", description="", vocabulary=[],
                        archetypal_entities={}, typical_relations=[])
                    for i in range(n)
                ]
            labels = [s.name for s in seeds]
            seeds_by_label = dict(zip(labels, seeds))

        def _run_one(label: str) -> MetaphorSpec:
            agent = TransformerAgent(
                style_hint=seeds_by_label[label],
                free_mode=free_domains,
                config=transformer_config,
                language=transformer_language,
            )
            return agent.run(problem)

        log.info(
            "Transformer.run start | n=%d model=%s free=%s units=%s",
            n, self.model, free_domains, labels,
        )
        t0 = time.perf_counter()
        results: list[MetaphorSpec] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = {pool.submit(_run_one, lbl): lbl for lbl in labels}
            for future in as_completed(futures):
                label = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    # Full traceback to the log file — UI gets short version
                    log.error(
                        "Transformer parallel run failed (unit=%s): %s\n%s",
                        label, exc, traceback.format_exc(),
                    )
                    errors.append(f"{label}: {exc}")

        # Stash partial errors so the UI can warn the user about silent fails
        # (e.g. you asked for 3 metaphors but only got 2 because one failed).
        self.last_transformer_errors = errors
        log.info(
            "Transformer.run done | %.2fs success=%d failed=%d",
            time.perf_counter() - t0, len(results), len(errors),
        )

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
        log.info(
            "Explorer.run start | move#%d force_different=%s directive=%r",
            len(self.session.moves) + 1,
            force_different,
            (directive[:40] + "…") if directive and len(directive) > 40 else directive,
        )
        t0 = time.perf_counter()
        try:
            move = self.explorer.run(
                metaphor=self.session.chosen_metaphor,
                history=self.session.moves,
                directive=directive,
                force_different=force_different,
            )
        except Exception:
            log.exception("Explorer.run failed after %.2fs", time.perf_counter() - t0)
            raise
        log.info(
            "Explorer.run done | %.2fs actor=%s",
            time.perf_counter() - t0, move.actor,
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
        log.info(
            "Translator.run start | n_moves=%d model=%s",
            len(self.session.moves), self.model,
        )
        t0 = time.perf_counter()
        try:
            solutions = self.translator.run(
                problem=self.session.problem,
                metaphor=self.session.chosen_metaphor,
                moves=self.session.moves,
            )
        except Exception:
            log.exception("Translator.run failed after %.2fs", time.perf_counter() - t0)
            raise
        log.info(
            "Translator.run done | %.2fs n_solutions=%d",
            time.perf_counter() - t0, len(solutions),
        )
        self.session.solutions = solutions
        return solutions

    def run_baseline(self) -> str:
        """Direct LLM answer without metaphor, for comparison panel."""
        if self.session.problem is None:
            raise RuntimeError("Run the Definer first.")
        return self.translator.baseline(self.session.problem)

    # --- evaluation: LLM-as-Judge (metaphor pipeline vs. baseline) ---
    @staticmethod
    def format_solutions_for_judge(solutions: list[Solution]) -> str:
        """Flatten the Translator's solutions into one prose answer.

        The judge compares whole answers, so we present the back-translations
        the same way a user would read them — numbered, original-domain only,
        WITHOUT the metaphor scaffolding or confidence/caveat machinery (the
        baseline has none of that, and showing it would leak which side is
        which and bias the judge).
        """
        return "\n\n".join(
            f"{i}. {s.original_domain_translation}"
            for i, s in enumerate(solutions, 1)
        )

    def run_judge(
        self,
        baseline_text: str | None = None,
        *,
        seed: int | None = None,
    ) -> ComparisonResult:
        """Blind-judge the Metaphor Machine answer against the baseline.

        Args:
            baseline_text: a previously generated baseline to reuse. If None,
                a fresh baseline is generated (so the comparison is always
                against the SAME model/problem). Passing the already-shown
                baseline avoids a second LLM call and judges exactly what the
                user saw.
            seed: forwarded to the judge's A/B randomisation for reproducibility.
        """
        if self.session.problem is None:
            raise RuntimeError("Run the Definer first.")
        if not self.session.solutions:
            raise RuntimeError("Run the Translator first — nothing to judge.")

        metaphor_answer = self.format_solutions_for_judge(self.session.solutions)
        baseline = baseline_text if baseline_text else self.run_baseline()

        log.info(
            "Judge.run start | model=%s n_solutions=%d",
            self.model, len(self.session.solutions),
        )
        t0 = time.perf_counter()
        try:
            result = self.judge.run(
                self.session.problem,
                metaphor_answer,
                baseline,
                seed=seed,
            )
        except Exception:
            log.exception("Judge.run failed after %.2fs", time.perf_counter() - t0)
            raise
        log.info(
            "Judge.run done | %.2fs winner=%s order=%s",
            time.perf_counter() - t0, result.winner, result.order,
        )
        return result

    def run_judge_batch(
        self,
        n: int = 5,
        baseline_text: str | None = None,
        *,
        base_seed: int = 0,
    ) -> list[ComparisonResult]:
        """Run the judge ``n`` times on the SAME answers and return all verdicts.

        Each run gets a different seed, so the A/B order is shuffled differently
        every time. A robust verdict should survive that shuffle; the spread
        across runs is exactly the position-bias signal. The baseline is
        generated once and reused across all runs, so every run judges the same
        two answers (only the presentation order changes) — and we don't pay for
        N baselines.

        Returns the list of per-run results; use ``summarize_runs`` to turn it
        into counts and a win-rate.
        """
        n = max(1, int(n))
        if self.session.problem is None:
            raise RuntimeError("Run the Definer first.")
        if not self.session.solutions:
            raise RuntimeError("Run the Translator first — nothing to judge.")

        baseline = baseline_text if baseline_text else self.run_baseline()
        log.info("Judge.batch start | n=%d model=%s", n, self.model)
        t0 = time.perf_counter()
        results = [
            self.run_judge(baseline_text=baseline, seed=base_seed + i)
            for i in range(n)
        ]
        log.info(
            "Judge.batch done | %.2fs n=%d", time.perf_counter() - t0, len(results)
        )
        return results
