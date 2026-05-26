"""Explorer agent — autonomously plays out the metaphor world.

The Explorer is the *generator*, not a reactor. It produces the next move on
its own initiative each turn, building on history. The user is a curator who
can:
  - accept the move (just keep going)
  - steer the next move with an optional directive ("focus on the quiet ones")
  - demand a structurally different strategy (force_different=True)
  - undo the last move (handled in the Pipeline / UI, not here)

See the assignment text and PLAN.md §2 — the system explores, the user makes
choices. Earlier implementation had this inverted, which exhausted users and
defeated the purpose.
"""

from __future__ import annotations

from ..core.schemas import MetaphorSpec, Move
from ..llm import LLMConfig
from ..prompts.check import find_forbidden
from .base import Agent

SYSTEM_PROMPT = """\
You are the EXPLORER inside a metaphor world. You are an autonomous narrator
— a game master who proposes the next scene yourself, not one who waits for
the player to dictate moves. Every turn you produce ONE concrete Move that
advances the exploration.

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
6. STRATEGIC DIVERSITY: when prior moves exist, the new move must try a
   structurally different strategy — not a variation of a prior move. If
   prior moves added rules, try a role-redistribution next; if they removed
   actors, try changing the environment instead.

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

    def __init__(
        self,
        config: LLMConfig | None = None,
        language: str = "en",
    ) -> None:
        super().__init__(
            name="explorer",
            system_prompt=SYSTEM_PROMPT,
            config=config or LLMConfig(temperature=0.7),
            language=language,  # type: ignore[arg-type]
        )

    def run(
        self,
        metaphor: MetaphorSpec,
        history: list[Move],
        directive: str | None = None,
        force_different: bool = False,
    ) -> Move:
        """Generate the next Move autonomously.

        Args:
            metaphor: the chosen MetaphorSpec.
            history: list of Moves already produced (the model sees them and
                must avoid repeating strategies).
            directive: optional user steering — e.g. "focus on the quiet
                druid" or "the previous consequence was unrealistic, try
                again". None means full autonomy.
            force_different: if True, an extra instruction tells the model
                to deliberately pick a strategy structurally unlike all
                prior moves. Used by the UI's "Try different angle" button.
        """
        messages = self._build_messages(metaphor, history, directive, force_different)
        # Inject language clause as the last system message so it takes priority.
        messages.insert(2, {"role": "system", "content": self.language_clause()})

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
            last_complaints = self._validate(move, metaphor, language=self.language)
            if not last_complaints:
                return move

        # Return best effort after max retries
        return move  # type: ignore[return-value]

    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(
        metaphor: MetaphorSpec,
        history: list[Move],
        directive: str | None,
        force_different: bool,
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
            history_text = "\n\n### Move history (you generated these)\n" + "\n\n".join(lines)

        # Build the instruction block
        if not history:
            task = (
                "Generate the FIRST move. Pick an actor and a tactically "
                "interesting opening action — something that probes the "
                "world's tensions rather than the most obvious thing to do."
            )
        elif force_different:
            task = (
                "Generate the NEXT move with a structurally DIFFERENT strategy "
                "from anything above. If prior moves changed rules, try changing "
                "roles. If prior moves changed roles, try changing the environment. "
                "If prior moves added structure, try removing structure. The "
                "diversity is the point — repeating strategies wastes the user's time."
            )
        else:
            task = (
                "Generate the NEXT move. React to the obstacle from the most "
                "recent move (work around it, or accept it as a new constraint), "
                "OR open a new front by trying a different angle. Do NOT repeat "
                "a strategy already tried."
            )

        if directive and directive.strip():
            task += (
                f"\n\nUser steering for this move: {directive.strip()}\n"
                "Honour the user's steering as much as the hard rules allow."
            )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": FORMAT_EXAMPLE},
            {
                "role": "user",
                "content": f"{world_context}{history_text}\n\n### Your task\n{task}\n\nReturn a Move JSON.",
            },
        ]

    @staticmethod
    def _validate(
        move: Move,
        metaphor: MetaphorSpec,
        language: str | None = None,
    ) -> list[str]:
        """Return a list of complaint strings (empty = valid)."""
        complaints: list[str] = []

        # Obstacle must be present
        if not move.obstacle or not move.obstacle.strip():
            complaints.append(
                "obstacle is missing or empty — name what physically or tactically "
                "resists this action."
            )

        # Check forbidden words across all text fields (language-aware)
        full_text = " ".join(
            filter(None, [move.actor, move.action, move.consequence, move.obstacle])
        )
        lang: str | None = language if language in ("en", "de") else None
        hits = find_forbidden(full_text, language=lang)  # type: ignore[arg-type]
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
