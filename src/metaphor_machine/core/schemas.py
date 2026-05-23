"""Pydantic schemas shared by all agents.

These are the *contracts* between agents. Treat changes here as breaking.
See PLAN.md §3 for the design rationale.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str
    role: str = Field(description='"actor" | "resource" | "obstacle" | "environment"')
    attributes: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    source: str
    target: str
    kind: str = Field(description='"depends_on" | "competes_with" | "transforms" | ...')
    strength: float = Field(default=0.5, ge=0.0, le=1.0)


class ProblemSpec(BaseModel):
    """Structured representation of the user's problem (output of Definer)."""

    raw_user_text: str
    summary: str
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    tensions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class Mapping(BaseModel):
    original: str
    metaphor: str
    fidelity: float = Field(ge=0.0, le=1.0)
    leak: str | None = Field(
        default=None,
        description="Where this mapping breaks down. Be honest — None is suspicious.",
    )


class MetaphorSpec(BaseModel):
    """A candidate metaphor world (output of one Transformer run)."""

    domain: str
    domain_intro: str
    mappings: list[Mapping]
    invariants_preserved: list[str] = Field(default_factory=list)
    invariants_broken: list[str] = Field(default_factory=list)


class Move(BaseModel):
    """One step in the Explorer's narrative."""

    actor: str
    action: str
    consequence: str
    obstacle: str | None = None


class Solution(BaseModel):
    """A candidate idea, with the back-translation."""

    metaphor_idea: str
    original_domain_translation: str
    confidence: float = Field(ge=0.0, le=1.0)
    caveats: list[str] = Field(default_factory=list)
