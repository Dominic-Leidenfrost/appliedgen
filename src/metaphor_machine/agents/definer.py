"""Definer agent - extracts a ProblemSpec from the user's raw description.

Sprint 1 implementation. Uses LLMClient.structured() with a tight system
prompt that forbids solution-suggesting and forces specificity.
"""

from __future__ import annotations

from ..core.schemas import ProblemSpec
from ..llm import LLMConfig
from .base import Agent

SYSTEM_PROMPT = """\
You are the DEFINER. Your job: turn a user's vague problem description into a
structured ProblemSpec. You are precise, not creative. You DO NOT suggest
solutions. You DO NOT use metaphors. You extract structure.

Rules:
- Be SPECIFIC. "The team is overwhelmed" is not a constraint. Instead:
  "team of 4 people, 12 active projects, 2 hard deadlines this month".
- Entities must be CONCRETE things the user mentions or clearly implies.
  Each entity has a role: "actor" | "resource" | "obstacle" | "environment".
- Relations connect two entities by name with a verb-like kind
  (e.g. "depends_on", "competes_with", "blocks").
- Tensions are CONTRADICTIONS in the problem itself - the things that make
  it actually hard ("must ship fast" vs. "must not break production").
- Unknowns are things you genuinely cannot infer and would need to ask the
  user. If the input is rich, this list may be short or empty.

When the user's input is too sparse to extract meaningful structure, you may
populate `unknowns` with up to 5 clarifying questions, but still produce a
valid ProblemSpec.
"""

# 1-shot format example: shows the SHAPE, not the content. Using a generic
# example (vending machine) so we don't bias toward the user's actual domain.
FORMAT_EXAMPLE = """\
Example input: "My vending machine sometimes eats coins without dispensing."

Example output:
{
  "raw_user_text": "My vending machine sometimes eats coins without dispensing.",
  "summary": "Coin-acceptance succeeds but product dispensing intermittently fails.",
  "entities": [
    {"name": "coin_acceptor", "role": "actor", "attributes": ["always accepts"]},
    {"name": "dispenser_motor", "role": "actor", "attributes": ["intermittent"]},
    {"name": "customer", "role": "actor", "attributes": ["expects product on payment"]},
    {"name": "coin", "role": "resource", "attributes": ["consumed on insertion"]}
  ],
  "relations": [
    {"source": "coin_acceptor", "target": "dispenser_motor", "kind": "should_trigger", "strength": 1.0},
    {"source": "customer", "target": "coin", "kind": "provides", "strength": 1.0}
  ],
  "constraints": [
    "must charge only on successful dispense",
    "must not require human intervention per transaction"
  ],
  "goals": [
    "every accepted coin results in a dispensed product OR a refund"
  ],
  "tensions": [
    "atomicity of payment+dispense vs. independent hardware components"
  ],
  "unknowns": [
    "frequency of the failure",
    "which product slots are affected",
    "any error code shown on the display"
  ]
}
"""


class DefinerAgent(Agent):
    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            name="definer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.2),
        )

    def run(self, user_text: str) -> ProblemSpec:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {"role": "user", "content": user_text},
        ]
        spec = self.client().structured(
            messages=messages,
            schema=ProblemSpec,
            agent_name=self.name,
        )
        # Guarantee raw_user_text round-trips even if the model paraphrases it.
        spec.raw_user_text = user_text
        return spec
