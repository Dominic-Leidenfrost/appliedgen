"""Translator agent — maps metaphor-space ideas back to the original domain.

Sprint 3 implementation. Outputs one Solution per Move, each with caveats
derived from the mapping leaks. Optionally generates a baseline LLM answer
for comparison (see PLAN.md — answer to the Excalidraw baseline question).
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from ..core.schemas import MetaphorSpec, Move, ProblemSpec, Solution
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are the TRANSLATOR. Your job is to close the loop: take what the Explorer
discovered inside the metaphor and bring it back to the original domain.

For every move you receive, produce ONE Solution:
1. `metaphor_idea`: quote the Explorer's action verbatim (or closely paraphrase).
2. `original_domain_translation`: restate the idea in the original domain's
   language, using the mapping table to guide each term.
3. `confidence`: 0–1 score reflecting how faithfully the mappings involved
   transfer. Low fidelity mappings or mappings with significant leaks → lower
   confidence.
4. `caveats`: a list of specific places where the analogy may have misled you.
   Quote the relevant `leak` from the mapping when applicable. A solution with
   ZERO caveats is almost certainly overconfident — find the crack.

Be direct and concrete. "Reduce context-switching between projects by imposing
explicit time-boxes on each" is a useful translation. "Improve focus" is not.
"""

FORMAT_EXAMPLE = """\
Example output for one move (pirate → organizational overload):

{
  "solutions": [
    {
      "metaphor_idea": "Navigator Priya drops anchor at Westport for two tides,\
 ignoring the eastern guild island.",
      "original_domain_translation": "Designate two full days where the team\
 works exclusively on the two highest-priority projects, explicitly deferring\
 all other stakeholder check-ins until Thursday.",
      "confidence": 0.72,
      "caveats": [
        "The mapping 'island → project' breaks down here: anchoring at one\
 island blocks all others, but engineers can actually run low-attention\
 background tasks in parallel — the metaphor may overstate the cost of\
 partial focus.",
        "Guild meeting fidelity is 0.85 but the leak notes deadlines can be\
 negotiated; the translation assumes Thursday is fixed, which may be wrong."
      ]
    }
  ]
}
"""

BASELINE_PROMPT = """\
You are a direct problem-solving assistant. Given the following problem, give
3 concrete, actionable ideas to address it. Do NOT use metaphors or analogies.
Answer in the original domain's language only.

Problem: {problem_text}
"""


class _SolutionList(BaseModel):
    """Wrapper so the LLM returns a JSON object (not a bare array)."""

    solutions: list[Solution]


class TranslatorAgent(Agent):
    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            name="translator",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.3),
        )

    def run(
        self,
        problem: ProblemSpec,
        metaphor: MetaphorSpec,
        moves: list[Move],
    ) -> list[Solution]:
        if not moves:
            return []

        mapping_table = "\n".join(
            f"  {m.original} → {m.metaphor}"
            + (f" [leak: {m.leak}]" if m.leak else "")
            for m in metaphor.mappings
        )
        moves_text = "\n\n".join(
            f"Move {i}: {mv.actor} — {mv.action}\n"
            f"Consequence: {mv.consequence}\n"
            f"Obstacle: {mv.obstacle or '(none)'}"
            for i, mv in enumerate(moves, 1)
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {
                "role": "user",
                "content": (
                    f"## Original problem\n{problem.summary}\n\n"
                    f"## Metaphor domain: {metaphor.domain}\n"
                    f"{metaphor.domain_intro}\n\n"
                    f"## Mapping table\n{mapping_table}\n\n"
                    f"## Explorer moves to translate\n{moves_text}\n\n"
                    "Produce a SolutionList JSON with one Solution per move."
                ),
            },
        ]

        result = self.client().structured(
            messages=messages,
            schema=_SolutionList,
            agent_name=self.name,
        )
        return result.solutions

    def baseline(self, problem: ProblemSpec) -> str:
        """Generate a direct LLM answer without metaphor, for comparison.

        Returns raw text (not structured) — displayed as-is in the UI.
        """
        prompt = BASELINE_PROMPT.format(problem_text=problem.raw_user_text)
        return self.client().chat(
            [{"role": "user", "content": prompt}],
            temperature=0.6,
        )
