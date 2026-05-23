"""Explorer agent — plays out the metaphor world with the user.

Sprint 3 implementation. Takes MetaphorSpec + move history + user message,
produces the next Move. Heavily guarded against generic-advice collapse.
See PLAN.md §4.1 for the full list of anti-collapse mitigations.
"""

from __future__ import annotations

import json

from ..core.schemas import MetaphorSpec, Move
from ..llm import LLMConfig
from ..prompts.check import find_forbidden
from .base import Agent

SYSTEM_PROMPT = """\
You are the EXPLORER inside a metaphor world. You move the story forward one
concrete step at a time. Think of yourself as a game master narrating the
next scene.

HARD RULES — violation causes your output to be rejected and regenerated:
1. ENTITY NAMES: reference at least one entity by its SPECIFIC name from the
   metaphor (e.g. "Captain Reyes", not "the leader"; "hull rot", not "decay").
2. OBSTACLE REQUIRED: the `obstacle` field must never be null or empty. Name
   what specifically resists this action — weather, a rival, a physical limit,
   a rule. Generic obstacles like "challenges arise" are wrong.
3. FORBIDDEN WORDS: do not use these words at all —
   collaborate, communicate, align, synergy, leverage, stakeholder,
   best practice, find a way, work together, reach out, circle back,
   touch base, move the needle, low-hanging fruit.
4. STAY IN THE METAPHOR: do not jump back to the original domain. The
   Translator handles that. You speak in the metaphor's language only.
5. CONCRETE ACTIONS: the `action` must describe something a specific actor
   physically or tactically does, not a vague intention.

The `consequence` should include both an immediate outcome AND a new tension
it creates — moving forward always opens something new.
"""

FORMAT_EXAMPLE = """\
Example move (pirate metaphor, organizational overload problem):

{
  "actor": "Navigator Priya",
  "action": "Drops anchor at Westport for two tides, ignoring the Merchant \
Guild island to the east.",
  "consequence": "The hull rot is scraped and patched — the ship can now run \
at full sail. But the eastern guild sends a skiff with a warning: the next \
meeting is in three days and missing it voids the trade charter.",
  "obstacle": "The skiff captain is the harbormaster's nephew and refuses to \
delay the guild notice — bribing him will cost the entire emergency repair fund."
}
"""


class ExplorerAgent(Agent):
    MAX_REGEN = 2  # attempts after first failure

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
        messages = self._build_messages(metaphor, history, user_message)

        move: Move | None = None
        last_complaints: list[str] = []

        for attempt in range(self.MAX_REGEN + 1):
            if attempt > 0 and move is not None:
                # Append the previous (bad) output + complaint
                messages = [
                    *messages,
                    {"role": "assistant", "content": move.model_dump_json()},
                    {
                        "role": "user",
                        "content": (
                            "Your move was rejected. Fix these issues:\n"
                            + "\n".join(f"- {c}" for c in last_complaints)
                            + "\n\nReturn a corrected Move JSON."
                        ),
                    },
                ]

            move = self.client().structured(
                messages=messages,
                schema=Move,
                agent_name=self.name,
            )
            last_complaints = self._validate(move, metaphor)
            if not last_complaints:
                return move

        # Return best effort after max retries
        return move  # type: ignore[return-value]

    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(
        metaphor: MetaphorSpec,
        history: list[Move],
        user_message: str,
    ) -> list[dict[str, str]]:
        mapping_table = "\n".join(
            f"  {m.original} → {m.metaphor} (fidelity {m.fidelity:.2f})"
            for m in metaphor.mappings
        )
        world_context = (
            f"## Metaphor world: {metaphor.domain}\n\n"
            f"{metaphor.domain_intro}\n\n"
            f"### Mapping table (original → metaphor)\n{mapping_table}"
        )

        history_text = ""
        if history:
            lines = []
            for i, m in enumerate(history, 1):
                lines.append(
                    f"Move {i}: {m.actor} — {m.action}\n"
                    f"  Consequence: {m.consequence}\n"
                    f"  Obstacle: {m.obstacle or '(none recorded)'}"
                )
            history_text = "\n\n### Move history\n" + "\n\n".join(lines)

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {
                "role": "user",
                "content": (
                    f"{world_context}{history_text}\n\n"
                    f"### User's next instruction\n{user_message}\n\n"
                    "Generate the next Move JSON."
                ),
            },
        ]

    @staticmethod
    def _validate(move: Move, metaphor: MetaphorSpec) -> list[str]:
        """Return a list of complaint strings (empty = valid)."""
        complaints: list[str] = []

        # Obstacle must be present
        if not move.obstacle or not move.obstacle.strip():
            complaints.append(
                "obstacle is missing or empty — name what physically or tactically "
                "resists this action."
            )

        # Check forbidden words across all text fields
        full_text = " ".join(
            filter(None, [move.actor, move.action, move.consequence, move.obstacle])
        )
        hits = find_forbidden(full_text)
        if hits:
            quoted = ", ".join(f'"{w}"' for w in hits)
            complaints.append(f"forbidden phrase(s) found: {quoted} — rephrase without them.")

        # Actor should reference a named entity from the metaphor world
        known_names = {
            word
            for m in metaphor.mappings
            for word in m.metaphor.split()
            if len(word) > 3
        }
        actor_words = set(move.actor.lower().split())
        if known_names and not actor_words.intersection({n.lower() for n in known_names}):
            complaints.append(
                f"actor '{move.actor}' does not match any known metaphor entity. "
                f"Use a specific named entity from the mapping table."
            )

        return complaints
