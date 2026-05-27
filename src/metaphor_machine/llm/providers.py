"""Provider registry for all supported LLM backends.

LiteLLM handles the actual API calls for all providers — we just need to
know which env var each provider reads, what model strings to pass, and
whether a key is currently set.

LiteLLM model-string conventions used here:
  Anthropic   → "anthropic/claude-sonnet-4-6"
  OpenAI      → "openai/gpt-4o"
  Gemini      → "gemini/gemini-2.5-flash"
  OpenRouter  → "openrouter/anthropic/claude-3.5-sonnet"

Note: Google removed the entire Gemini 1.5 family in late 2025 — those
model IDs now return HTTP 404 from generativelanguage.googleapis.com.
The curated list below tracks the 2.5 family (and the "*-latest" aliases
that auto-roll forward). The UI also pulls the live ListModels response
on every Gemini selection, so this list is purely a fallback for when
the live fetch fails.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ModelOption:
    display: str    # shown in UI dropdown
    model_id: str   # LiteLLM model string


@dataclass
class Provider:
    key: str                          # internal identifier
    display: str                      # shown in UI
    env_var: str                      # env var that holds the API key
    models: list[ModelOption] = field(default_factory=list)
    notes: str = ""                   # shown as help text in UI

    def is_available(self) -> bool:
        return bool(os.getenv(self.env_var))

    def default_model(self) -> str:
        return self.models[0].model_id if self.models else ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PROVIDERS: list[Provider] = [
    Provider(
        key="anthropic",
        display="Anthropic",
        env_var="ANTHROPIC_API_KEY",
        models=[
            ModelOption("Claude Sonnet 4.6 (recommended)", "anthropic/claude-sonnet-4-6"),
            ModelOption("Claude Haiku 4.5 (fast/cheap)", "anthropic/claude-haiku-4-5"),
            ModelOption("Claude Opus 4.7 (most capable)", "anthropic/claude-opus-4-7"),
        ],
        notes="Set ANTHROPIC_API_KEY in .env",
    ),
    Provider(
        key="openai",
        display="OpenAI",
        env_var="OPENAI_API_KEY",
        models=[
            ModelOption("GPT-4o", "openai/gpt-4o"),
            ModelOption("GPT-4o mini (fast/cheap)", "openai/gpt-4o-mini"),
            ModelOption("GPT-4 Turbo", "openai/gpt-4-turbo"),
        ],
        notes="Set OPENAI_API_KEY in .env",
    ),
    Provider(
        key="gemini",
        display="Google Gemini",
        env_var="GEMINI_API_KEY",
        # Verified against ListModels on 2026-05-27 — the 1.5 family is
        # gone (HTTP 404), the 2.5 family is the current stable line.
        # The "*-latest" aliases auto-roll forward, so they're useful as
        # a stable default that won't go stale.
        models=[
            ModelOption("Gemini 2.5 Flash (recommended)", "gemini/gemini-2.5-flash"),
            ModelOption("Gemini 2.5 Pro (most capable)", "gemini/gemini-2.5-pro"),
            ModelOption("Gemini 2.5 Flash-Lite (fast/cheap)", "gemini/gemini-2.5-flash-lite"),
            ModelOption("Gemini 2.0 Flash", "gemini/gemini-2.0-flash"),
            ModelOption("Gemini Flash Latest (auto-rolling)", "gemini/gemini-flash-latest"),
            ModelOption("Gemini Pro Latest (auto-rolling)", "gemini/gemini-pro-latest"),
        ],
        notes="Set GEMINI_API_KEY in .env — get one free at aistudio.google.com",
    ),
    Provider(
        key="openrouter",
        display="OpenRouter",
        env_var="OPENROUTER_API_KEY",
        models=[
            ModelOption("Claude 3.5 Sonnet (via OpenRouter)", "openrouter/anthropic/claude-3.5-sonnet"),
            ModelOption("Gemini Pro 1.5 (via OpenRouter)", "openrouter/google/gemini-pro-1.5"),
            ModelOption("Mixtral 8x7B (via OpenRouter)", "openrouter/mistralai/mixtral-8x7b-instruct"),
            ModelOption("Llama 3.1 70B (via OpenRouter)", "openrouter/meta-llama/llama-3.1-70b-instruct"),
        ],
        notes="Set OPENROUTER_API_KEY in .env — access to 100+ models at openrouter.ai",
    ),
]

# Fast lookup by key
PROVIDER_MAP: dict[str, Provider] = {p.key: p for p in PROVIDERS}


def available_providers() -> list[Provider]:
    """Return providers that have an API key set in the environment."""
    return [p for p in PROVIDERS if p.is_available()]


def provider_for_model(model_id: str) -> Provider | None:
    """Guess which provider owns a given model string."""
    for p in PROVIDERS:
        if any(m.model_id == model_id for m in p.models):
            return p
        # Also match by prefix (e.g. "anthropic/..." → anthropic)
        prefix = model_id.split("/")[0]
        if prefix == p.key:
            return p
    return None


def check_key_for_model(model_id: str) -> str | None:
    """Return a human-readable error if the required key is missing, else None."""
    provider = provider_for_model(model_id)
    if provider is None:
        return None  # unknown provider — let LiteLLM error naturally
    if not provider.is_available():
        return (
            f"Model '{model_id}' requires {provider.display} — "
            f"set {provider.env_var} in your .env file. {provider.notes}"
        )
    return None
