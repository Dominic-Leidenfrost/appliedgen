"""Forbidden-word enforcement for agent outputs.

See PLAN.md §4.1. Load from forbidden_words.yaml so the list is configurable
without code changes. Used by ExplorerAgent (Sprint 3) and Transformer validation.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_YAML_PATH = Path(__file__).parent / "forbidden_words.yaml"
_cached_words: list[str] | None = None


def _load() -> list[str]:
    global _cached_words
    if _cached_words is None:
        with _YAML_PATH.open() as f:
            data = yaml.safe_load(f)
        _cached_words = [w.lower() for w in data.get("forbidden", [])]
    return _cached_words


def find_forbidden(text: str) -> list[str]:
    """Return every forbidden phrase found (lowercased) in text."""
    haystack = text.lower()
    return [w for w in _load() if re.search(r"\b" + re.escape(w) + r"\b", haystack)]


def assert_clean(text: str) -> None:
    """Raise ValueError listing all forbidden phrases if any are found."""
    hits = find_forbidden(text)
    if hits:
        quoted = ", ".join(f'"{w}"' for w in hits)
        raise ValueError(f"Output contains forbidden phrase(s): {quoted}")
