"""Definer agent - extracts a ProblemSpec from the user's raw description.

Uses LLMClient.structured() with a tight system
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

# Format-only template: it demonstrates the SHAPE of a valid ProblemSpec using
# abstract placeholders, never real content. Placeholders (<...>) make it
# impossible to copy verbatim, which previously caused the model to echo a
# concrete example (the "vending machine / coins" leak) instead of analysing
# the user's actual input.
FORMAT_EXAMPLE = """\
FORMAT TEMPLATE — STRUCTURE ONLY.

This is NOT a problem to solve and NOT example content. It only shows which
fields a valid ProblemSpec has and what type each holds. NEVER reuse any of
these placeholder strings, names, or values in your answer. Always extract
every value from the user's actual input (provided in the user message below).
If you ever output the literal placeholders below, you have made a mistake.

{
  "raw_user_text": "<the user's input, verbatim>",
  "summary": "<one neutral sentence describing the user's problem>",
  "entities": [
    {"name": "<concrete_thing_from_user_input>", "role": "actor", "attributes": ["<attribute>"]},
    {"name": "<another_concrete_thing>", "role": "resource", "attributes": ["<attribute>"]}
  ],
  "relations": [
    {"source": "<entity_name>", "target": "<other_entity_name>", "kind": "<verb_like_relation>", "strength": 1.0}
  ],
  "constraints": [
    "<a hard constraint stated or implied by the user>"
  ],
  "goals": [
    "<what success looks like for the user>"
  ],
  "tensions": [
    "<a real contradiction inside the user's problem>"
  ],
  "unknowns": [
    "<something you cannot infer and would need to ask the user>"
  ]
}
"""


class DefinerAgent(Agent):
    def __init__(
        self,
        config: LLMConfig | None = None,
        language: str = "en",
    ) -> None:
        super().__init__(
            name="definer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.2),
            language=language,  # type: ignore[arg-type]
        )

    def run(self, user_text: str) -> ProblemSpec:
        # The user's text is wrapped in explicit delimiters so the model can
        # never confuse it with the format template above, and a final
        # instruction re-anchors it on this input (recency helps weaker models).
        user_block = (
            "Analyse ONLY the problem between the markers below. Extract every "
            "field of the ProblemSpec from THIS text. Do not use the format "
            "template's placeholder values.\n"
            "<<<USER_PROBLEM\n"
            f"{user_text}\n"
            "USER_PROBLEM>>>"
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {"role": "system", "content": self.language_clause()},
            {"role": "user", "content": user_block},
        ]
        spec = self.client().structured(
            messages=messages,
            schema=ProblemSpec,
            agent_name=self.name,
        )
        # Guarantee raw_user_text round-trips even if the model paraphrases it.
        spec.raw_user_text = user_text
        return spec
