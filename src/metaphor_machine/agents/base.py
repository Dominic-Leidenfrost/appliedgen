"""Base class shared by all four agents."""

from __future__ import annotations

from dataclasses import dataclass

from ..llm import LLMClient, LLMConfig


@dataclass
class Agent:
    """Stateless agent. Holds its own LLMConfig (temperature etc.) and a
    system prompt. Subclasses implement `run(...)` with a typed signature."""

    name: str
    system_prompt: str
    config: LLMConfig

    def client(self) -> LLMClient:
        return LLMClient(self.config)
