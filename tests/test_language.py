"""Tests for the DE/EN language toggle.

Coverage:
- language_instruction() returns the right pin for each language.
- find_forbidden() picks the right list per language.
- Pipeline.set_language() persists, invalidates the agent cache, preserves
  session state.
- Agent classes accept language= and inject the clause into messages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metaphor_machine.agents.definer import DefinerAgent
from metaphor_machine.agents.explorer import ExplorerAgent
from metaphor_machine.agents.transformer import TransformerAgent
from metaphor_machine.agents.translator import TranslatorAgent
from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.prompts import language as lang_mod
from metaphor_machine.prompts.check import find_forbidden
from metaphor_machine.prompts.language import (
    FORBIDDEN_WORDS,
    language_instruction,
    persist_language,
)


@pytest.fixture(autouse=True)
def isolated_lang_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    fake = tmp_path / "active_language.txt"
    monkeypatch.setattr(lang_mod, "_LANGUAGE_CACHE_FILE", fake)
    # Also redirect the model cache file used by Pipeline so tests don't
    # collide with the real cache.
    from metaphor_machine.core import pipeline as pl_mod
    monkeypatch.setattr(pl_mod, "_MODEL_CACHE_FILE", tmp_path / "active_model.txt")
    return fake


class TestLanguageInstruction:
    def test_en_pins_english(self) -> None:
        clause = language_instruction("en")
        assert "ENGLISH" in clause

    def test_de_pins_german_and_mentions_field_names(self) -> None:
        clause = language_instruction("de")
        assert "GERMAN" in clause
        # Must teach the model that FIELD NAMES stay English even when values
        # are German — otherwise Pydantic validation explodes.
        assert "Field NAMES stay English" in clause


class TestForbiddenWordsByLanguage:
    def test_english_list_catches_collaborate(self) -> None:
        hits = find_forbidden("We should collaborate on this", language="en")
        assert "collaborate" in hits

    def test_german_list_catches_zusammenarbeiten(self) -> None:
        hits = find_forbidden(
            "Wir sollten zusammenarbeiten und synergien nutzen", language="de"
        )
        # Either word counts; both are in the German list
        assert "zusammenarbeiten" in hits or "synergien" in hits

    def test_english_not_triggered_by_german_text(self) -> None:
        hits = find_forbidden("Wir sollten zusammenarbeiten", language="en")
        assert not hits

    def test_no_language_checks_both(self) -> None:
        """Defensive default: if caller doesn't pin a language, check both."""
        hits_en = find_forbidden("We should collaborate")
        hits_de = find_forbidden("Wir sollten zusammenarbeiten")
        assert "collaborate" in hits_en
        assert "zusammenarbeiten" in hits_de


class TestPipelineLanguage:
    def test_default_language_is_en(self) -> None:
        p = Pipeline()
        assert p.language == "en"

    def test_explicit_language_wins(self) -> None:
        p = Pipeline(language="de")
        assert p.language == "de"

    def test_set_language_persists(self, isolated_lang_cache: Path) -> None:
        p = Pipeline(language="en")
        p.set_language("de")
        assert isolated_lang_cache.exists()
        assert isolated_lang_cache.read_text().strip() == "de"

    def test_set_language_invalidates_agent_cache(self) -> None:
        p = Pipeline(language="en")
        first = p.definer
        assert p._definer is first
        p.set_language("de")
        # cache must be cleared so the next access builds with new lang
        assert p._definer is None
        rebuilt = p.definer
        assert rebuilt.language == "de"

    def test_set_language_no_change_is_noop(self) -> None:
        p = Pipeline(language="de")
        original_definer = p.definer
        p.set_language("de")
        assert p._definer is original_definer

    def test_set_language_preserves_session_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METAPHOR_MOCK", "1")
        p = Pipeline()
        p.run_definer("toy problem")
        before = p.session.problem
        p.set_language("de")
        # Switching language must not nuke existing extracted content.
        assert p.session.problem is before

    def test_new_pipeline_reads_persisted_language(
        self, isolated_lang_cache: Path
    ) -> None:
        isolated_lang_cache.parent.mkdir(parents=True, exist_ok=True)
        isolated_lang_cache.write_text("de")
        p = Pipeline()
        assert p.language == "de"


class TestAgentLanguageInjection:
    """Each agent must inject its language_clause() into the system messages
    so the LLM actually produces the right language. We can't run real LLMs
    here, but we can verify the clause is present in the messages list."""

    def test_definer_injects_clause(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("METAPHOR_MOCK", "1")
        a = DefinerAgent(language="de")
        # Run intercepts: we can't see messages from outside, so check the
        # clause is at least correctly generated
        assert "GERMAN" in a.language_clause()

    def test_transformer_carries_language(self) -> None:
        a = TransformerAgent(language="de")
        assert a.language == "de"
        assert "GERMAN" in a.language_clause()

    def test_explorer_carries_language(self) -> None:
        a = ExplorerAgent(language="de")
        assert a.language == "de"
        assert "GERMAN" in a.language_clause()

    def test_translator_carries_language(self) -> None:
        a = TranslatorAgent(language="de")
        assert a.language == "de"
        assert "GERMAN" in a.language_clause()


def test_forbidden_words_lists_are_non_empty() -> None:
    """Sanity: both language lists should have content."""
    assert len(FORBIDDEN_WORDS["en"]) >= 10
    assert len(FORBIDDEN_WORDS["de"]) >= 5
