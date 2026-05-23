"""Tests for the LLM client — focused on JSON extraction and mock-mode path.

These tests do NOT call a real LLM. The structured() real path is exercised by
the agent tests via the mock registry.
"""

from __future__ import annotations

import json

import pytest

from metaphor_machine.core.schemas import ProblemSpec
from metaphor_machine.llm import LLMClient, LLMConfig
from metaphor_machine.llm.mock import mock_enabled


# --- JSON extraction --------------------------------------------------------

class TestExtractJSON:
    def test_plain_json(self) -> None:
        assert LLMClient._extract_json('{"a": 1}') == {"a": 1}

    def test_with_prose_prefix(self) -> None:
        text = 'Sure, here is your JSON:\n{"a": 1, "b": [2, 3]}'
        assert LLMClient._extract_json(text) == {"a": 1, "b": [2, 3]}

    def test_markdown_fenced(self) -> None:
        text = '```json\n{"a": 1}\n```'
        assert LLMClient._extract_json(text) == {"a": 1}

    def test_bare_markdown_fence(self) -> None:
        text = '```\n{"a": 1}\n```'
        assert LLMClient._extract_json(text) == {"a": 1}

    def test_no_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            LLMClient._extract_json("no JSON in here")


# --- mock mode --------------------------------------------------------------

class TestMockMode:
    def test_mock_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("METAPHOR_MOCK", raising=False)
        assert not mock_enabled()

    def test_mock_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("METAPHOR_MOCK", "1")
        assert mock_enabled()

    def test_structured_returns_validated_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METAPHOR_MOCK", "1")
        client = LLMClient(LLMConfig(model="anthropic/claude-haiku-4-5"))
        problem = client.structured(
            messages=[{"role": "user", "content": "I have too many priorities"}],
            schema=ProblemSpec,
            agent_name="definer",
        )
        assert isinstance(problem, ProblemSpec)
        assert "too many priorities" in problem.raw_user_text
        # Mock data should pass schema validation including nested entities
        assert problem.entities
        assert problem.entities[0].role in {"actor", "resource", "obstacle", "environment"}


# --- schema hint ------------------------------------------------------------

def test_schema_hint_includes_field_names() -> None:
    hint = LLMClient._schema_hint(ProblemSpec)
    assert "raw_user_text" in hint
    assert "JSON" in hint
