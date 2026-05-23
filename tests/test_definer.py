"""Tests for the Definer agent (mock-mode end-to-end)."""

from __future__ import annotations

import pytest

from metaphor_machine.agents.definer import DefinerAgent
from metaphor_machine.core.pipeline import Pipeline
from metaphor_machine.core.schemas import ProblemSpec


@pytest.fixture(autouse=True)
def enable_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METAPHOR_MOCK", "1")


class TestDefinerAgent:
    def test_run_returns_problemspec(self) -> None:
        agent = DefinerAgent()
        result = agent.run("I have a small team and too many priorities.")
        assert isinstance(result, ProblemSpec)
        assert "small team" in result.raw_user_text

    def test_run_preserves_user_text_verbatim(self) -> None:
        agent = DefinerAgent()
        text = "Some very specific input the mock would otherwise overwrite."
        result = agent.run(text)
        # Definer.run() must overwrite raw_user_text with the user's text
        # even if the mock returned something different.
        assert result.raw_user_text == text

    def test_run_produces_at_least_one_entity(self) -> None:
        agent = DefinerAgent()
        result = agent.run("anything goes here")
        assert len(result.entities) >= 1


class TestPipelineDefiner:
    def test_pipeline_stores_problem(self) -> None:
        pipeline = Pipeline()
        assert pipeline.session.problem is None
        pipeline.run_definer("test problem")
        assert pipeline.session.problem is not None
        assert pipeline.session.raw_input == "test problem"

    def test_transformer_blocks_without_definer(self) -> None:
        pipeline = Pipeline()
        with pytest.raises(RuntimeError, match="Definer first"):
            pipeline.run_transformer()
