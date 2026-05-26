"""Tests for the runtime model switch (Pipeline.set_model)."""

from __future__ import annotations

import pytest

from metaphor_machine.core.pipeline import Pipeline


class TestSetModel:
    def test_constructor_explicit_model_wins(self) -> None:
        p = Pipeline(model="gemini/gemini-1.5-pro")
        assert p.model == "gemini/gemini-1.5-pro"

    def test_constructor_falls_back_to_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("METAPHOR_DEFAULT_MODEL", "openai/gpt-4o")
        p = Pipeline()
        assert p.model == "openai/gpt-4o"

    def test_set_model_changes_model(self) -> None:
        p = Pipeline(model="anthropic/claude-haiku-4-5")
        p.set_model("gemini/gemini-1.5-flash")
        assert p.model == "gemini/gemini-1.5-flash"

    def test_set_model_drops_cached_agents(self) -> None:
        p = Pipeline(model="anthropic/claude-haiku-4-5")
        original_definer = p.definer  # force lazy construction
        assert p._definer is original_definer
        p.set_model("gemini/gemini-1.5-flash")
        # Cache must be cleared so the next access builds a new agent with the
        # new model — otherwise the model switch silently does nothing.
        assert p._definer is None
        new_definer = p.definer
        assert new_definer is not original_definer
        assert new_definer.config.model == "gemini/gemini-1.5-flash"

    def test_set_model_no_change_is_noop(self) -> None:
        p = Pipeline(model="anthropic/claude-haiku-4-5")
        original_definer = p.definer
        p.set_model("anthropic/claude-haiku-4-5")  # same as current
        # Same model → cache should NOT be invalidated (would waste a call to
        # rebuild the agent for no reason).
        assert p._definer is original_definer

    def test_set_model_preserves_session_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METAPHOR_MOCK", "1")
        p = Pipeline(model="anthropic/claude-haiku-4-5")
        p.run_definer("toy problem")
        problem_before = p.session.problem
        p.set_model("gemini/gemini-1.5-flash")
        # The cached ProblemSpec must survive a model switch — otherwise users
        # lose all progress every time they tweak the dropdown.
        assert p.session.problem is problem_before

    def test_agent_temperatures_match_plan(self) -> None:
        """Each agent must use the per-role temperature from PLAN.md §2."""
        p = Pipeline(model="gemini/gemini-1.5-pro")
        assert p.definer.config.temperature == 0.2
        assert p.explorer.config.temperature == 0.7
        assert p.translator.config.temperature == 0.3
        # Transformer is built per-call inside run_transformer; check via the
        # private helper that constructs its config.
        assert p._config_for("transformer").temperature == 0.9
