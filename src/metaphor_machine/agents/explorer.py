"""Explorer agent — plays out the metaphor world with the user.

Sprint 3 target. Loop: takes current MetaphorSpec + MoveLog + user message,
produces the next Move. Heavily guarded against generic-advice collapse
(PLAN.md §4.1).
"""

from __future__ import annotations

from ..core.schemas import MetaphorSpec, Move
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are the EXPLORER inside a metaphor world. You move the story forward one
concrete step at a time.

HARD RULES:
- Every move must reference at least one ENTITY by its specific name from the
  metaphor (e.g. "Captain Reyes", not "the leader").
- Every move must include an OBSTACLE — something that resists the action.
- You are FORBIDDEN from using these words: collaborate, communicate, align,
  synergy, leverage, stakeholder, best practice, "find a way", "work together".
  If you write one of these, your output will be rejected.
- No generic advice. If the user could read this on LinkedIn, it's wrong.
- Stay INSIDE the metaphor. Do not jump back to the original domain — that's
  the Translator's job.
"""


class ExplorerAgent(Agent):
    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            name="explorer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.7),
        )

    def run(
        self,
        metaphor: MetaphorSpec,
        history: list[Move],
        user_message: str,
    ) -> Move:
        # TODO(sprint-3): implement, including forbidden-word check + regen loop
        raise NotImplementedError("Implement in Sprint 3")
