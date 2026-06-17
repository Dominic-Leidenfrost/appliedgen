"""Judge agent — blind, randomised pairwise evaluation of two answers.

Why this exists
---------------
The Metaphor Machine produces solutions to open-ended problems, so there is no
ground-truth "correct" answer to score against. Reviewers at the poster session
repeatedly flagged this: *how do you know the output is any good?*

The honest answer is a *relative* one. We compare the full Metaphor Machine
answer against the cheapest sensible baseline — asking the same model the same
problem directly, with no metaphor (``Translator.baseline``). A third model, the
JUDGE, reads both answers blind and picks the better one overall and per
criterion. Run over a set of problems this yields a **win-rate**: a single,
defensible number ("the metaphor pipeline was preferred in N % of cases").

Position bias
-------------
LLM judges are known to favour whichever answer is shown first. We control for
this two ways:
  1. Per call we randomise which answer is labelled "A" vs "B" (see ``seed``).
  2. The judge only ever sees neutral labels A/B — never "metaphor"/"baseline".
The agent then de-anonymises the verdict back into ComparisonResult.

The judge runs at temperature 0.0 for repeatability.
"""

from __future__ import annotations

import random

from ..core.schemas import (
    JUDGE_CRITERIA,
    ComparisonResult,
    JudgeVerdict,
    ProblemSpec,
)
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are an impartial JUDGE. You are given a PROBLEM and two candidate answers,
labelled "Answer A" and "Answer B". You do not know how either was produced and
you must not speculate about it. Judge only what is written.

Score the two answers on these criteria, each independently:
- specificity: concrete and detailed vs. vague and generic.
- actionability: can the reader actually DO this, with named steps?
- novelty: does it offer a non-obvious angle, or just the first thing anyone
  would say?
- relevance: does it actually address THIS problem, its constraints and
  tensions — not a vaguely related one?

For every criterion pick a winner: "A", "B", or "tie". Then pick an OVERALL
winner ("A", "B", or "tie") — this is a holistic call, not just a majority vote
of the criteria, though it should usually agree with them.

Be discriminating. "tie" is allowed but do not reach for it to avoid deciding;
use it only when the two answers are genuinely indistinguishable on that point.
Do NOT reward length, confident tone, or formatting. Reward substance.
"""

FORMAT_EXAMPLE = """\
Respond with a JudgeVerdict JSON. Example shape:

{
  "winner": "A",
  "criteria": [
    {"name": "specificity", "winner": "A",
     "rationale": "A names concrete time-boxes; B says 'improve focus'."},
    {"name": "actionability", "winner": "A",
     "rationale": "A gives steps the team can run on Monday; B is aspirational."},
    {"name": "novelty", "winner": "tie",
     "rationale": "Both reach for fairly standard prioritisation ideas."},
    {"name": "relevance", "winner": "B",
     "rationale": "B engages the deadline tension directly; A sidesteps it."}
  ],
  "reasoning": "A is more concrete and actionable, which dominates here,\
 though B engages the core deadline tension more directly. On balance A is the\
 stronger, more usable answer."
}
"""


class JudgeAgent(Agent):
    """Blind pairwise judge. Stateless like the other agents."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        language: str = "en",
    ) -> None:
        super().__init__(
            name="judge",
            system_prompt=SYSTEM_PROMPT,
            # temperature 0 → deterministic, so re-running the eval is stable.
            config=config or LLMConfig(temperature=0.0),
            language=language,  # type: ignore[arg-type]
        )

    def run(
        self,
        problem: ProblemSpec,
        metaphor_answer: str,
        baseline_answer: str,
        *,
        seed: int | None = None,
    ) -> ComparisonResult:
        """Compare the two answers and return a de-anonymised result.

        Args:
            problem: the problem both answers respond to.
            metaphor_answer: the Metaphor Machine's final answer (back-translated
                solutions joined into prose).
            baseline_answer: the direct, no-metaphor answer (Translator.baseline).
            seed: optional seed for the A/B coin flip. Pass a fixed value in
                batch evaluation so a run is reproducible; leave None for a
                fresh random assignment each call.
        """
        rng = random.Random(seed)
        metaphor_first = rng.random() < 0.5
        if metaphor_first:
            answer_a, answer_b = metaphor_answer, baseline_answer
        else:
            answer_a, answer_b = baseline_answer, metaphor_answer

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {"role": "system", "content": self.language_clause()},
            {
                "role": "user",
                "content": (
                    f"## Problem\n{problem.summary or problem.raw_user_text}\n\n"
                    f"## Answer A\n{answer_a.strip()}\n\n"
                    f"## Answer B\n{answer_b.strip()}\n\n"
                    "Judge the two answers as instructed and return a "
                    "JudgeVerdict JSON."
                ),
            },
        ]

        verdict = self.client().structured(
            messages=messages,
            schema=JudgeVerdict,
            agent_name=self.name,
        )
        return self._deanonymise(verdict, metaphor_first)

    # ------------------------------------------------------------------
    # A/B  ->  metaphor/baseline
    # ------------------------------------------------------------------
    @staticmethod
    def _deanonymise(verdict: JudgeVerdict, metaphor_first: bool) -> ComparisonResult:
        """Translate the judge's blind A/B picks back to which side they mean."""

        def label(side: str) -> str:
            s = (side or "").strip().lower()
            if s == "a":
                return "metaphor" if metaphor_first else "baseline"
            if s == "b":
                return "baseline" if metaphor_first else "metaphor"
            return "tie"  # "tie" or anything unexpected

        criteria_winners: dict[str, str] = {}
        for cv in verdict.criteria:
            name = (cv.name or "").strip().lower()
            if name in JUDGE_CRITERIA:
                criteria_winners[name] = label(cv.winner)

        return ComparisonResult(
            winner=label(verdict.winner),
            criteria_winners=criteria_winners,
            reasoning=verdict.reasoning,
            order="metaphor_first" if metaphor_first else "baseline_first",
        )
