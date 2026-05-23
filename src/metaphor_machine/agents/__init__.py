"""The four agents. Each one is a thin class that owns a prompt + a schema."""

from .base import Agent
from .definer import DefinerAgent

__all__ = ["Agent", "DefinerAgent"]
