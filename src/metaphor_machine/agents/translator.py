"""Translator agent — maps metaphor-space ideas back to the original domain.

Sprint 3 target. Output must include caveats: where the analogy may have
misled us. The "leak" report is half the value of the system.
"""

from __future__ import annotations

from ..core.schemas import MetaphorSpec, Move, ProblemSpec, Solution
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are the TRANSLATOR. Given a problem, the metaphor it was mapped onto, and
a list of moves inside that metaphor — translate the interesting moves back to
the ORIGINAL domain.

For each candidate solution you produce:
- State the metaphor-space idea verbatim.
- Translate it to the original domain using the mappings from MetaphorSpec.
- Give a confidence score (0–1) based on the fidelity of the mappings involved.
- List CAVEATS: places where the analogy may have produced an answer that
  doesn't survive the translation. Be honest. A solution with no caveats is
  suspicious.
"""


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
        # TODO(sprint-3): implement
        raise NotImplementedError("Implement in Sprint 3")
