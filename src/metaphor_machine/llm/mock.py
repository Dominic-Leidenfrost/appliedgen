"""Mock LLM responses for offline dev + tests.

Activated when env var METAPHOR_MOCK is truthy. The registry maps agent
names to factory functions; each factory receives the schema and the chat
messages so it can build a plausible-looking response. The point is to
exercise the full pipeline (UI, validation, storage) without burning API
credits or needing a key.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from pydantic import BaseModel


def mock_enabled() -> bool:
    return os.getenv("METAPHOR_MOCK", "").lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Per-agent mock factories
# ---------------------------------------------------------------------------

def _definer_mock(schema: type[BaseModel], messages: list[dict[str, str]]) -> dict[str, Any]:
    """Return a canned ProblemSpec.

    Echoes the user's text in `raw_user_text` so the UI shows something
    related to what they typed. The rest is intentionally generic — this
    is a smoke test, not a real extraction.
    """
    user_text = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    return {
        "raw_user_text": user_text,
        "summary": "[MOCK] Generic problem extracted without LLM call.",
        "entities": [
            {"name": "user", "role": "actor", "attributes": ["overwhelmed"]},
            {"name": "task_backlog", "role": "resource", "attributes": ["growing"]},
        ],
        "relations": [
            {
                "source": "user",
                "target": "task_backlog",
                "kind": "manages",
                "strength": 0.6,
            }
        ],
        "constraints": ["[MOCK] limited time", "[MOCK] limited attention"],
        "goals": ["[MOCK] reduce overwhelm", "[MOCK] make progress"],
        "tensions": ["[MOCK] speed vs. quality"],
        "unknowns": ["[MOCK] which task matters most"],
    }


def _transformer_mock(schema: type[BaseModel], messages: list[dict[str, str]]) -> dict[str, Any]:
    """Return a canned MetaphorSpec so the UI is testable without API keys."""
    return {
        "domain": "pirate_adventure",
        "domain_intro": (
            "[MOCK] A crew of four sails between twelve contested islands, each claimed "
            "by a different merchant guild. Two guild meetings loom this month. "
            "The captain cannot abandon any island without political fallout. "
            "Hull rot spreads silently below the waterline."
        ),
        "mappings": [
            {
                "original": "engineer (actor)",
                "metaphor": "crew member",
                "fidelity": 0.8,
                "leak": "Crew members are fungible; engineers have non-interchangeable skills.",
            },
            {
                "original": "active project (resource)",
                "metaphor": "island under sail",
                "fidelity": 0.75,
                "leak": "A ship can only be in one place; engineers can context-switch (badly).",
            },
            {
                "original": "stakeholder deadline (constraint)",
                "metaphor": "guild meeting at port",
                "fidelity": 0.85,
                "leak": "Guild meetings are binary; deadlines can sometimes be negotiated.",
            },
            {
                "original": "quality slipping (tension)",
                "metaphor": "hull rot below the waterline",
                "fidelity": 0.7,
                "leak": "Hull rot is invisible until catastrophic; quality signals are often visible earlier.",
            },
        ],
        "invariants_preserved": [
            "[MOCK] resource scarcity forces prioritisation",
            "[MOCK] missing a critical event has cascading consequences",
        ],
        "invariants_broken": [
            "[MOCK] projects can run in parallel; a ship cannot",
        ],
    }


def _explorer_mock(schema: type[BaseModel], messages: list[dict[str, str]]) -> dict[str, Any]:
    """Return a canned Move — stays inside pirate metaphor, has obstacle."""
    return {
        "actor": "Navigator Priya",
        "action": (
            "[MOCK] Drops anchor at Westport for two tides, ignoring the eastern "
            "guild island, to scrape the hull rot off the keel."
        ),
        "consequence": (
            "The ship can now run at full sail. But the eastern guild sends a skiff "
            "with a warning: the next meeting is in three days and missing it voids "
            "the trade charter."
        ),
        "obstacle": (
            "The skiff captain is the harbormaster's nephew and refuses to delay the "
            "guild notice — the repair fund barely covers the dock fee."
        ),
    }


def _translator_mock(schema: type[BaseModel], messages: list[dict[str, str]]) -> dict[str, Any]:
    """Return a canned SolutionList wrapper."""
    return {
        "solutions": [
            {
                "metaphor_idea": (
                    "[MOCK] Navigator Priya drops anchor at Westport for two tides, "
                    "ignoring the eastern guild island."
                ),
                "original_domain_translation": (
                    "[MOCK] Designate two full days where the team works exclusively "
                    "on the two highest-priority projects, deferring all other "
                    "stakeholder check-ins until Thursday."
                ),
                "confidence": 0.72,
                "caveats": [
                    "[MOCK] The 'island → project' mapping breaks down: anchoring "
                    "blocks all others, but engineers can run low-attention background "
                    "tasks — the metaphor may overstate the cost of partial focus.",
                    "[MOCK] Guild meeting fidelity 0.85 but leak notes deadlines can "
                    "be negotiated; translation assumes Thursday is fixed.",
                ],
            }
        ]
    }


MOCK_REGISTRY: dict[str, Callable[[type[BaseModel], list[dict[str, str]]], dict[str, Any]]] = {
    "definer": _definer_mock,
    "transformer": _transformer_mock,
    "explorer": _explorer_mock,
    "translator": _translator_mock,
}
