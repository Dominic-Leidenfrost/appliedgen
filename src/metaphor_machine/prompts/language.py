"""Language management: German / English toggle.

Why this module exists: every agent's output text (summary, entity names,
metaphor descriptions, move narration, solution translations) should be in
the user's chosen language. The Pydantic field names stay English because
they are part of the JSON schema, but every value inside those fields gets
generated in the chosen language.

Persistence: like the model choice, the language preference survives page
reloads via data/cache/active_language.txt.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

Language = Literal["en", "de"]
DEFAULT_LANGUAGE: Language = "en"

_PROMPTS_DIR = Path(__file__).resolve().parent
_FORBIDDEN_WORDS_FILES: dict[Language, Path] = {
    "en": _PROMPTS_DIR / "forbidden_words.yaml",
    "de": _PROMPTS_DIR / "forbidden_words_de.yaml",
}


@lru_cache(maxsize=2)
def load_forbidden_words(lang: Language) -> list[str]:
    """Load the forbidden phrases for one language from YAML."""
    path = _FORBIDDEN_WORDS_FILES[lang]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    words = data.get("forbidden", [])
    if not isinstance(words, list):
        raise ValueError(f"Invalid forbidden words file: {path}")
    return [str(word) for word in words]


# Backward-compatible mapping for existing callers/tests.
FORBIDDEN_WORDS: dict[Language, list[str]] = {
    lang: load_forbidden_words(lang) for lang in ("en", "de")
}


def language_instruction(lang: Language) -> str:
    """Return the system-prompt suffix that pins the output language.

    Schema field names stay English. Only values translate.
    """
    if lang == "de":
        return (
            "LANGUAGE: All text VALUES in your JSON output (summary, names, "
            "attributes, descriptions, actions, consequences, translations, "
            "caveats, etc.) must be in GERMAN. Field NAMES stay English. "
            "Example: {\"summary\": \"Kleines Team mit zu vielen Projekten\", "
            "\"entities\": [{\"name\": \"engineer\", \"attributes\": "
            "[\"ueberlastet\"]}]} - note 'summary'/'name'/'attributes' stay "
            "English but their values are German."
        )
    return "LANGUAGE: All text values in your JSON output must be in ENGLISH."


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
