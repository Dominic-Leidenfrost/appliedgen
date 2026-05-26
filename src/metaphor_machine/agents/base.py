"""Base class shared by all four agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..llm import LLMClient, LLMConfig
from ..prompts.language import language_instruction

Language = Literal["en", "de"]


@dataclass
class Agent:
    """Stateless agent. Holds its own LLMConfig (temperature etc.), a system
    prompt, and a language preference (en/de) that gets injected into the
    prompt so all *values* in the JSON output land in the right language."""

    name: str
    system_prompt: str
    config: LLMConfig
    language: Language = field(default="en")

    def client(self) -> LLMClient:
        return LLMClient(self.config)

    def language_clause(self) -> str:
        """The system-prompt suffix that pins output values to self.language."""
        return language_instruction(self.language)
