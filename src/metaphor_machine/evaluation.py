"""Reusable batch-evaluation logic for the LLM-as-Judge.

Both the CLI (``scripts/eval_judge.py``) and the Streamlit Evaluation mode call
into here, so the "run the whole pipeline N times and judge it" behaviour lives
in exactly one place.

For each problem we run the full pipeline (Definer → Transformer → Explorer →
Translator), generate the no-metaphor baseline, and have the judge compare them
``runs`` times (each run reshuffles the blind A/B order). The result is a
win-rate per problem and overall — the defensible number the poster reviewers
asked for.
"""

from __future__ import annotations

from .agents.judge import summarize_runs
from .core.pipeline import Pipeline
from .core.schemas import ComparisonResult
from .logging_config import get_logger

log = get_logger(__name__)


def evaluate_problem(
    problem_text: str,
    *,
    model: str | None = None,
    language: str | None = None,
    n_metaphors: int = 3,
    moves: int = 3,
    runs: int = 5,
    free_domains: bool = False,
    base_seed: int = 0,
    on_stage=None,
) -> dict:
    """Run the full pipeline for one problem and judge it ``runs`` times.

    Args:
        on_stage: optional callback ``fn(stage: str)`` invoked BEFORE each
            slow step (each is one or more LLM calls). Lets a UI show what the
            pipeline is doing right now instead of looking frozen.

    Returns a dict with the per-run results, an aggregate summary, and the two
    answers that were compared (handy for display / debugging).
    """

    def stage(s: str) -> None:
        if on_stage:
            on_stage(s)

    pipe = Pipeline(model=model, language=language)
    stage("Definer")
    pipe.run_definer(problem_text)
    stage(f"Transformer ({n_metaphors} metaphors)")
    candidates = pipe.run_transformer(n=n_metaphors, free_domains=free_domains)
    # Auto-curate: take the first candidate (a human would choose here).
    pipe.session.chosen_metaphor = candidates[0]
    for k in range(max(0, moves)):
        stage(f"Explorer move {k + 1}/{moves}")
        pipe.run_explorer_turn()
    stage("Translator")
    pipe.run_translator()

    stage("Baseline")
    baseline = pipe.run_baseline()
    # Judge run-by-run (rather than run_judge_batch) so we can report progress.
    results: list[ComparisonResult] = []
    for i in range(max(1, runs)):
        stage(f"Judge {i + 1}/{max(1, runs)}")
        results.append(pipe.run_judge(baseline_text=baseline, seed=base_seed + i))
    return {
        "problem_text": problem_text,
        "problem_summary": pipe.session.problem.summary if pipe.session.problem else "",
        "domain": pipe.session.chosen_metaphor.domain if pipe.session.chosen_metaphor else "",
        "metaphor_answer": Pipeline.format_solutions_for_judge(pipe.session.solutions),
        "baseline": baseline,
        "results": results,
        "summary": summarize_runs(results),
    }


def run_evaluation(
    problems: list,
    *,
    model: str | None = None,
    language: str | None = None,
    n_metaphors: int = 3,
    moves: int = 3,
    runs: int = 5,
    free_domains: bool = False,
    progress=None,
) -> dict:
    """Evaluate a list of problems and aggregate across all of them.

    Args:
        problems: list of problem strings, OR dicts with at least ``user_text``
            (and optionally ``id`` / ``category``) — matches the shape of
            ``tests/fixtures/problems.yaml``.
        progress: optional callback ``fn(done, total, label)``. Called at the
            START of every problem AND before each pipeline stage within a
            problem, so a UI can show the live stage (e.g. "p1 · Judge 3/5")
            instead of looking frozen during the long LLM calls.

    Returns a dict with ``per_problem`` (one entry per problem) and ``overall``
    (counts + win-rate pooled across every judge run of every problem).
    """
    per_problem = []
    overall_results: list[ComparisonResult] = []
    total = len(problems)

    for i, p in enumerate(problems):
        if isinstance(p, dict):
            text = p.get("user_text", "")
            pid = p.get("id", f"problem_{i + 1}")
            category = p.get("category", "")
        else:
            text = str(p)
            pid = f"problem_{i + 1}"
            category = ""

        def _stage(stage: str, _i=i, _pid=pid) -> None:
            if progress:
                progress(_i, total, f"{_pid} · {stage}")

        if progress:
            progress(i, total, f"{pid} · starting")

        try:
            ev = evaluate_problem(
                text,
                model=model,
                language=language,
                n_metaphors=n_metaphors,
                moves=moves,
                runs=runs,
                free_domains=free_domains,
                base_seed=i * 1000,  # disjoint seed ranges per problem
                on_stage=_stage,
            )
        except Exception as exc:  # one bad problem shouldn't sink the batch
            log.exception("evaluate_problem failed for %s", pid)
            per_problem.append(
                {"id": pid, "category": category, "error": f"{type(exc).__name__}: {exc}"}
            )
            continue

        ev["id"] = pid
        ev["category"] = category
        per_problem.append(ev)
        overall_results.extend(ev["results"])

    if progress:
        progress(total, total, "done")

    return {
        "per_problem": per_problem,
        "overall": summarize_runs(overall_results),
        "params": {
            "model": model,
            "language": language,
            "n_metaphors": n_metaphors,
            "moves": moves,
            "runs": runs,
            "free_domains": free_domains,
        },
    }
