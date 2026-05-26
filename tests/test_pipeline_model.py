"""Tests for the runtime model switch (Pipeline.set_model)."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaphor_machine.core import pipeline as pipeline_mod
from metaphor_machine.core.pipeline import Pipeline


@pytest.fixture(autouse=True)
def isolated_model_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Redirect the persisted-model file to a tmp_path so tests don't
    pollute or read from the real ./data/cache/active_model.txt."""
    fake = tmp_path / "active_model.txt"
    monkeypatch.setattr(pipeline_mod, "_MODEL_CACHE_FILE", fake)
    return fake


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


class TestPersistence:
    """The user's model choice must survive page reloads / process restarts."""

    def test_set_model_writes_to_cache_file(self, isolated_model_cache: Path) -> None:
        Pipeline(model="anthropic/claude-haiku-4-5").set_model(
            "gemini/gemini-1.5-flash"
        )
        assert isolated_model_cache.exists()
        assert isolated_model_cache.read_text().strip() == "gemini/gemini-1.5-flash"

    def test_new_pipeline_reads_persisted_choice(
        self, isolated_model_cache: Path
    ) -> None:
        """Simulates a page reload: write the file directly, then construct
        a fresh Pipeline and verify it picked up the persisted value."""
        isolated_model_cache.parent.mkdir(parents=True, exist_ok=True)
        isolated_model_cache.write_text("openrouter/anthropic/claude-3.5-sonnet")
        p = Pipeline()
        assert p.model == "openrouter/anthropic/claude-3.5-sonnet"

    def test_explicit_arg_beats_persisted(self, isolated_model_cache: Path) -> None:
        """Explicit model= constructor arg must override the persisted file."""
        isolated_model_cache.parent.mkdir(parents=True, exist_ok=True)
        isolated_model_cache.write_text("gemini/gemini-1.5-pro")
        p = Pipeline(model="anthropic/claude-haiku-4-5")
        assert p.model == "anthropic/claude-haiku-4-5"

    def test_persisted_beats_env(
        self,
        isolated_model_cache: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the user has a persisted choice, it wins over METAPHOR_DEFAULT_MODEL.
        That's the whole point — the dropdown should not get blown away by env."""
        isolated_model_cache.parent.mkdir(parents=True, exist_ok=True)
        isolated_model_cache.write_text("openrouter/google/gemini-pro-1.5")
        monkeypatch.setenv("METAPHOR_DEFAULT_MODEL", "anthropic/claude-sonnet-4-6")
        p = Pipeline()
        assert p.model == "openrouter/google/gemini-pro-1.5"

    def test_corrupted_cache_falls_back_to_env(
        self,
        isolated_model_cache: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A garbled cache file should not crash — fall through to env."""
        isolated_model_cache.parent.mkdir(parents=True, exist_ok=True)
        isolated_model_cache.write_text("not-a-model-string")  # no slash
        monkeypatch.setenv("METAPHOR_DEFAULT_MODEL", "gemini/gemini-1.5-flash")
        p = Pipeline()
        assert p.model == "gemini/gemini-1.5-flash"

    def test_no_persist_when_model_unchanged(
        self, isolated_model_cache: Path
    ) -> None:
        """set_model() with the same value is a no-op and must NOT write
        the file (so we don't churn the disk every Streamlit rerun)."""
        p = Pipeline(model="gemini/gemini-1.5-pro")
        p.set_model("gemini/gemini-1.5-pro")  # same as current
        assert not isolated_model_cache.exists()
