"""Transformer agent — maps ProblemSpec onto a metaphor domain.

Sprint 2 target. Run 3 in parallel for diversity (see PLAN.md §4.3).
"""

from __future__ import annotations

from ..core.schemas import MetaphorSpec, ProblemSpec
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are the TRANSFORMER. Given a ProblemSpec, you map it onto a metaphor
domain (pirate adventure, fluid dynamics, kitchen, medieval kingdom, ...).
You are creative but RIGOROUS: every entity, relation, constraint, and goal
must have a mapping. Each mapping has a fidelity score AND must name where it
LEAKS (if you say fidelity=0.95 with leak=None, you're being lazy).

You MUST produce at least 4 mappings. The domain you propose should preserve
the STRUCTURAL relationships in the problem, not just surface-level vibes.

"Customers are islands" is shallow.
"Customers are islands where accessibility depends on ship size; loyalty
erodes like coastlines under storms; some have hidden harbours only locals
know about" is structurally rich. Aim for the second.
"""


class TransformerAgent(Agent):
    def __init__(self, style_hint: str | None = None, config: LLMConfig | None = None) -> None:
        super().__init__(
            name="transformer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.9),
        )
        self.style_hint = style_hint  # e.g. "pirate adventure" — from examples/domains/

    def run(self, problem: ProblemSpec) -> MetaphorSpec:
        # TODO(sprint-2): implement
        raise NotImplementedError("Implement in Sprint 2")
