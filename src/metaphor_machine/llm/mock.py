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


MOCK_REGISTRY: dict[str, Callable[[type[BaseModel], list[dict[str, str]]], dict[str, Any]]] = {
    "definer": _definer_mock,
    # TODO(sprint-2): add transformer mock
    # TODO(sprint-3): add explorer + translator mocks
}
