"""Forbidden-word enforcement for agent outputs.

See PLAN.md §4.1. Used by ExplorerAgent (Sprint 3) and Transformer validation.

The list is language-aware: when language='de', we check the German
weasel-word list instead of the English one. Backward-compatible callers
that don't pass a language fall through to the union of both lists (catches
either language regardless).
"""

from __future__ import annotations

import re
from typing import Literal

from .language import FORBIDDEN_WORDS

Language = Literal["en", "de"]


def _words_for(language: Language | None) -> list[str]:
    if language in ("en", "de"):
        return [w.lower() for w in FORBIDDEN_WORDS[language]]
    # No language pinned → check both lists (defensive)
    return [w.lower() for words in FORBIDDEN_WORDS.values() for w in words]


def find_forbidden(text: str, language: Language | None = None) -> list[str]:
    """Return every forbidden phrase found (lowercased) in text."""
    haystack = text.lower()
    return [
        w for w in _words_for(language)
        if re.search(r"\b" + re.escape(w) + r"\b", haystack)
    ]


def assert_clean(text: str, language: Language | None = None) -> None:
    """Raise ValueError listing all forbidden phrases if any are found."""
    hits = find_forbidden(text, language=language)
    if hits:
        quoted = ", ".join(f'"{w}"' for w in hits)
        raise ValueError(f"Output contains forbidden phrase(s): {quoted}")
