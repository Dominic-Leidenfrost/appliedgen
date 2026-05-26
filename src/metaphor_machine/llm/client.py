"""Thin provider-agnostic LLM wrapper built on LiteLLM.

Why LiteLLM: same interface for Anthropic + OpenAI, supports structured outputs
on both via `response_format`, and has built-in retry/streaming. Saves us from
writing two adapters.

Mock mode: set METAPHOR_MOCK=1 in the env to skip real LLM calls. Tests and
no-API-key dev use this. See `mock.py` for the fixture registry.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .mock import MOCK_REGISTRY, mock_enabled
from .providers import check_key_for_model

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMConfig:
    model: str = "anthropic/claude-sonnet-4-6"
    temperature: float = 0.7
    max_tokens: int = 2048


class LLMError(RuntimeError):
    """Raised when the LLM call fails after all retries."""


class StructuredOutputError(LLMError):
    """Raised when the LLM cannot produce schema-valid output after retries."""


class LLMClient:
    """Wraps litellm.completion with sensible defaults + retries.

    Usage:
        client = LLMClient()
        text = client.chat([{"role": "user", "content": "Hello"}])

        problem = client.structured(
            messages=[...],
            schema=ProblemSpec,
        )
    """

    # How many times we re-ask the model after a Pydantic validation failure.
    STRUCTURED_RETRIES = 2

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig(
            model=os.getenv("METAPHOR_DEFAULT_MODEL", "anthropic/claude-sonnet-4-6"),
            temperature=float(os.getenv("METAPHOR_DEFAULT_TEMPERATURE", "0.7")),
        )

    # ----- raw text completion --------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        # LLMError comes from our key-check / config — retrying never helps.
        # Only transient network/provider errors should be retried.
        retry=retry_if_not_exception_type(LLMError),
        reraise=True,
    )
    def chat(self, messages: list[dict[str, str]], **overrides: Any) -> str:
        """Simple text completion. Lazy-imports litellm so the package can be
        installed-but-unused without crashing imports.

        Raises:
            LLMError: missing API key for the requested model (no retries).
            Exception: re-raised after up to 3 retries with exponential backoff.
        """
        import litellm

        model = overrides.get("model", self.config.model)

        # Raise early with a human-readable message if the key is missing.
        key_error = check_key_for_model(model)
        if key_error:
            raise LLMError(key_error)

        resp = litellm.completion(
            model=model,
            messages=messages,
            temperature=overrides.get("temperature", self.config.temperature),
            max_tokens=overrides.get("max_tokens", self.config.max_tokens),
        )
        return resp.choices[0].message.content or ""

    # ----- structured (Pydantic) output -----------------------------------

    def structured(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        agent_name: str | None = None,
        **overrides: Any,
    ) -> T:
        """Return an instance of `schema` parsed from the model's JSON output.

        Strategy:
          1. If METAPHOR_MOCK is set and a fixture exists for `agent_name`,
             return that fixture (no LLM call).
          2. Else: ask the LLM for JSON matching the schema, parse, validate.
          3. On Pydantic validation failure: re-prompt with the error message
             included, up to STRUCTURED_RETRIES times.
        """
        # --- mock path ----------------------------------------------------
        if mock_enabled() and agent_name and agent_name in MOCK_REGISTRY:
            fixture = MOCK_REGISTRY[agent_name](schema, messages)
            return schema.model_validate(fixture)

        # --- real path ----------------------------------------------------
        schema_hint = self._schema_hint(schema)
        local_messages = [
            *messages,
            {"role": "system", "content": schema_hint},
        ]

        last_error: str | None = None
        for attempt in range(self.STRUCTURED_RETRIES + 1):
            if last_error is not None:
                local_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response did not validate. "
                            f"Error:\n{last_error}\n\n"
                            "Reply with JSON only, no prose, matching the schema."
                        ),
                    }
                )
            raw = self.chat(local_messages, **overrides)
            try:
                payload = self._extract_json(raw)
                return schema.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)
                continue
        raise StructuredOutputError(
            f"Failed to produce schema-valid output after "
            f"{self.STRUCTURED_RETRIES + 1} attempts. Last error: {last_error}"
        )

    # ----- helpers --------------------------------------------------------

    @staticmethod
    def _schema_hint(schema: type[BaseModel]) -> str:
        """Build a system message describing the expected JSON shape."""
        try:
            json_schema = schema.model_json_schema()
        except Exception:
            json_schema = {}
        return (
            "Respond ONLY with valid JSON matching this Pydantic schema. "
            "No prose, no markdown fences, no explanation — just the JSON object.\n\n"
            f"Schema: {json.dumps(json_schema, indent=2)}"
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Pull the first JSON object out of a model response.

        Models sometimes wrap JSON in ```json fences or add a sentence before
        it. We strip that and parse the first {...} block.
        """
        # Strip markdown code fences if present
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))
        # Otherwise grab the first balanced object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise json.JSONDecodeError("no JSON object found", text, 0)
        return json.loads(text[start : end + 1])
