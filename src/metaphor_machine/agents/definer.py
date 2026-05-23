"""Definer agent — extracts ProblemSpec from the user's raw description.

Sprint 1 target. Implementation lives here.
"""

from __future__ import annotations

from ..core.schemas import ProblemSpec
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are the DEFINER. Your job: turn a user's vague problem description into a
structured ProblemSpec. You are precise, not creative. You DO NOT suggest
solutions. You DO ask up to 5 clarifying questions if the input is too vague —
but only if absolutely necessary.

Required output: a ProblemSpec with entities, relations, constraints, goals,
tensions, and unknowns. Be specific. "The team is overwhelmed" is not a
constraint — "team of 4, 12 active projects, 2 deadlines this month" is.
"""


class DefinerAgent(Agent):
    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            name="definer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.2),
        )

    def run(self, user_text: str) -> ProblemSpec:
        # TODO(sprint-1): call self.client().structured(...) with the schema
        raise NotImplementedError("Implement in Sprint 1")
