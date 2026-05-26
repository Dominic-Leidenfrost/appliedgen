"""Language management — German / English toggle.

Why this module exists: every agent's output text (summary, entity names,
metaphor descriptions, move narration, solution translations) should be in
the user's chosen language. The Pydantic FIELD NAMES stay English (they're
the JSON schema and must match Pydantic's expectations), but every VALUE
inside those fields gets generated in the chosen language.

Persistence: like the model choice, the language preference survives page
reloads via data/cache/active_language.txt.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

Language = Literal["en", "de"]
DEFAULT_LANGUAGE: Language = "en"

# Forbidden phrases per language. The Explorer regenerates if any of these
# appear in its output. English list is the original; German list targets
# the equivalent Beratergeschwurbel.
FORBIDDEN_WORDS: dict[Language, list[str]] = {
    "en": [
        "collaborate", "communicate", "align", "synergy", "leverage",
        "stakeholder", "best practice", "find a way", "work together",
        "reach out", "circle back", "touch base", "move the needle",
        "low-hanging fruit",
    ],
    "de": [
        "zusammenarbeiten", "kommunizieren", "abstimmen", "synergie",
        "synergien", "stakeholder", "best practice", "einen weg finden",
        "miteinander arbeiten", "auf augenhöhe", "den dialog suchen",
        "die richtige balance finden", "ganzheitlich",
    ],
}


def language_instruction(lang: Language) -> str:
    """Returns the system-prompt suffix that pins the output language.

    Schema field NAMES stay English (Pydantic), only VALUES translate.
    """
    if lang == "de":
        return (
            "LANGUAGE: All text VALUES in your JSON output (summary, names, "
            "attributes, descriptions, actions, consequences, translations, "
            "caveats, etc.) must be in GERMAN. Field NAMES stay English. "
            "Example: {\"summary\": \"Kleines Team mit zu vielen Projekten\", "
            "\"entities\": [{\"name\": \"engineer\", \"attributes\": "
            "[\"überlastet\"]}]} — note 'summary'/'name'/'attributes' stay "
            "English but their values are German."
        )
    return (
        "LANGUAGE: All text values in your JSON output must be in ENGLISH."
    )


# ---------------------------------------------------------------------------
# Persistence (analogous to pipeline._persist_model)
# ---------------------------------------------------------------------------

_LANGUAGE_CACHE_FILE = Path(
    os.getenv("METAPHOR_CACHE_DIR", "./data/cache")
) / "active_language.txt"


def load_persisted_language() -> Language | None:
    try:
        text = _LANGUAGE_CACHE_FILE.read_text().strip().lower()
        if text in ("en", "de"):
            return text  # type: ignore[return-value]
    except (OSError, FileNotFoundError):
        pass
    return None


def persist_language(lang: Language) -> None:
    """Best-effort write. Silent on disk/perm errors."""
    try:
        _LANGUAGE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LANGUAGE_CACHE_FILE.write_text(lang)
    except OSError:
        pass


def resolve_language(
    explicit: Language | None = None,
    env_var: str = "METAPHOR_LANGUAGE",
) -> Language:
    """Resolve the active language with precedence:
    explicit arg > persisted file > env var > DEFAULT_LANGUAGE.
    """
    if explicit in ("en", "de"):
        return explicit  # type: ignore[return-value]
    persisted = load_persisted_language()
    if persisted:
        return persisted
    env = (os.getenv(env_var, "") or "").strip().lower()
    if env in ("en", "de"):
        return env  # type: ignore[return-value]
    return DEFAULT_LANGUAGE
