"""Thin provider-agnostic LLM wrapper built on LiteLLM.

Why LiteLLM: same interface for Anthropic + OpenAI, supports structured outputs
on both via `response_format`, and has built-in retry/streaming. Saves us from
writing two adapters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class LLMConfig:
    model: str = "anthropic/claude-sonnet-4-6"
    temperature: float = 0.7
    max_tokens: int = 2048


class LLMClient:
    """Wraps litellm.completion with sensible defaults + retries.

    Usage:
        client = LLMClient()
        text = client.chat([{"role": "user", "content": "Hello"}])

    For structured outputs (Sprint 1+):
        problem = client.structured(
            messages=[...],
            schema=ProblemSpec,
        )
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig(
            model=os.getenv("METAPHOR_DEFAULT_MODEL", "anthropic/claude-sonnet-4-6"),
            temperature=float(os.getenv("METAPHOR_DEFAULT_TEMPERATURE", "0.7")),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def chat(self, messages: list[dict[str, str]], **overrides: Any) -> str:
        """Simple text completion. Lazy-import litellm so the package can be
        installed-but-unused without crashing imports (handy for tests)."""
        import litellm

        resp = litellm.completion(
            model=overrides.get("model", self.config.model),
            messages=messages,
            temperature=overrides.get("temperature", self.config.temperature),
            max_tokens=overrides.get("max_tokens", self.config.max_tokens),
        )
        return resp.choices[0].message.content or ""

    def structured(self, messages: list[dict[str, str]], schema: Any, **overrides: Any) -> Any:
        """Structured-output call. Returns an instance of `schema` (Pydantic).

        TODO(sprint-1): implement with litellm's response_format + Pydantic
        validation + 2 retries with the validation error appended to the prompt.
        """
        raise NotImplementedError("Structured outputs — implement in Sprint 1")
