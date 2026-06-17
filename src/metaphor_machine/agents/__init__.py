"""The four agents. Each one is a thin class that owns a prompt + a schema."""

from .base import Agent
from .definer import DefinerAgent
from .judge import JudgeAgent

__all__ = ["Agent", "DefinerAgent", "JudgeAgent"]
