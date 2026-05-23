"""Transformer agent — maps ProblemSpec onto a metaphor domain.

Sprint 2 implementation. Three instances run in parallel (see Pipeline)
each seeded with a different domain hint from examples/domains/*.yaml.
See PLAN.md §4.3.
"""

from __future__ import annotations

import json

from ..core.schemas import Mapping, MetaphorSpec, ProblemSpec
from ..llm import LLMConfig
from ..prompts.domains import DomainSeed
from .base import Agent

SYSTEM_PROMPT = """\
You are the TRANSFORMER. Given a structured ProblemSpec and a target domain
style hint, you produce a MetaphorSpec: a rich, structurally faithful metaphor.

RULES:
1. Produce AT LEAST 4 mappings — one per major entity or relation in the problem.
2. Every mapping MUST have a `leak` field that names where the mapping breaks
   down or oversimplifies. fidelity=0.9 with leak=null is lazy — find the crack.
3. The domain must PRESERVE relational structure, not just surface mood.
   "Customers are islands" is shallow.
   "Customers are islands where accessibility depends on ship size; loyalty
   erodes like coastlines under storms" is structurally rich. Aim higher.
4. `invariants_preserved` lists structural properties that map cleanly.
   `invariants_broken` lists structural properties the metaphor cannot capture.
5. Stay inside your assigned domain. Do not mix metaphors.
6. The `domain_intro` (3–4 sentences) sets the scene so the Explorer can
   immediately act inside it without further explanation.
"""

FORMAT_EXAMPLE = """\
Example (organizational overload → pirate adventure):
{
  "domain": "pirate_adventure",
  "domain_intro": "A small crew of four sails between twelve contested islands,
    each claimed by a different merchant guild. Two guild meetings loom this
    month — miss them and the crew loses trading rights. The captain cannot
    abandon any island without political fallout from the guilds.",
  "mappings": [
    {
      "original": "engineer (actor)",
      "metaphor": "crew member",
      "fidelity": 0.85,
      "leak": "Crew members are fungible; engineers have specialised skills that
        cannot be swapped without loss."
    },
    {
      "original": "active project (resource)",
      "metaphor": "island under sail",
      "fidelity": 0.8,
      "leak": "Islands are physical locations; projects are parallel, not
        sequential — the ship can only be in one place but an engineer can
        context-switch."
    },
    {
      "original": "stakeholder deadline (constraint)",
      "metaphor": "guild meeting at port",
      "fidelity": 0.9,
      "leak": "Guild meetings are binary (attend or not); deadlines are softer
        and can sometimes be negotiated."
    },
    {
      "original": "quality slipping (tension)",
      "metaphor": "hull rot below the waterline",
      "fidelity": 0.75,
      "leak": "Hull rot is invisible until catastrophic; quality slip often has
        visible warning signals that this metaphor hides."
    }
  ],
  "invariants_preserved": [
    "resource scarcity forces prioritisation",
    "missing a critical event has cascading consequences",
    "captain (lead) cannot unilaterally drop commitments"
  ],
  "invariants_broken": [
    "projects can run in parallel; a ship cannot sail to two islands at once",
    "knowledge transfer costs are absent from the ship metaphor"
  ]
}
"""


class TransformerAgent(Agent):
    def __init__(
        self,
        style_hint: str | DomainSeed | None = None,
        config: LLMConfig | None = None,
    ) -> None:
        super().__init__(
            name="transformer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.9),
        )
        # Accept a raw string OR a DomainSeed dataclass
        if isinstance(style_hint, str):
            self.style_hint_text = style_hint
        elif style_hint is not None:
            self.style_hint_text = style_hint.as_style_hint()
        else:
            self.style_hint_text = None

    def run(self, problem: ProblemSpec) -> MetaphorSpec:
        problem_json = json.dumps(problem.model_dump(), indent=2)

        hint_block = (
            f"\n\nDomain style hint (you MUST use this domain):\n{self.style_hint_text}"
            if self.style_hint_text
            else ""
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {
                "role": "user",
                "content": (
                    f"Here is the ProblemSpec to transform:{hint_block}\n\n"
                    f"```json\n{problem_json}\n```\n\n"
                    "Produce a MetaphorSpec. Remember: ≥4 mappings, every mapping "
                    "needs a leak, fidelity must be honest."
                ),
            },
        ]

        metaphor = self.client().structured(
            messages=messages,
            schema=MetaphorSpec,
            agent_name=self.name,
        )

        return self._validate_and_tighten(metaphor, messages)

    # ------------------------------------------------------------------

    def _validate_and_tighten(
        self, metaphor: MetaphorSpec, messages: list[dict]
    ) -> MetaphorSpec:
        """Re-prompt once if quality checks fail."""
        complaints: list[str] = []

        if len(metaphor.mappings) < 4:
            complaints.append(
                f"You only produced {len(metaphor.mappings)} mappings. Need ≥4."
            )

        lazy = [
            m.original
            for m in metaphor.mappings
            if m.fidelity > 0.9 and m.leak is None
        ]
        if lazy:
            names = ", ".join(f'"{n}"' for n in lazy)
            complaints.append(
                f"Mapping(s) {names} have fidelity > 0.9 but no leak — "
                "find where each one breaks down."
            )

        if not complaints:
            return metaphor

        # One regeneration attempt with the complaints appended.
        messages = [
            *messages,
            {"role": "assistant", "content": metaphor.model_dump_json()},
            {
                "role": "user",
                "content": (
                    "Your MetaphorSpec failed quality checks:\n"
                    + "\n".join(f"- {c}" for c in complaints)
                    + "\n\nRevise and return a corrected MetaphorSpec JSON."
                ),
            },
        ]
        return self.client().structured(
            messages=messages,
            schema=MetaphorSpec,
            agent_name=self.name,
        )

    @staticmethod
    def _pick_diverse_mappings(
        candidates: list[MetaphorSpec], n: int = 3
    ) -> list[MetaphorSpec]:
        """Naïve diversity filter: prefer candidates with distinct domain names."""
        seen_domains: set[str] = set()
        diverse: list[MetaphorSpec] = []
        for c in candidates:
            d = c.domain.lower().split("_")[0]
            if d not in seen_domains:
                diverse.append(c)
                seen_domains.add(d)
            if len(diverse) == n:
                break
        # Pad with remaining if we didn't find n distinct ones
        for c in candidates:
            if c not in diverse:
                diverse.append(c)
            if len(diverse) == n:
                break
        return diverse[:n]
