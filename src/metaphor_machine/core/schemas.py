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


# ---------------------------------------------------------------------------
# Evaluation — LLM-as-Judge (blind pairwise comparison)
# ---------------------------------------------------------------------------
#
# The Metaphor Machine has no ground-truth "correct" answer, so we cannot
# measure absolute quality. We CAN measure *relative* quality: does the
# metaphor detour beat simply asking the model directly (the Translator's
# baseline())? A separate judge model reads both answers blind and picks the
# better one per criterion. Aggregated over many problems this yields a
# win-rate — a single hard number for the poster. See agents/judge.py.

# The criteria the judge scores. Kept here so the agent, the prompt and the
# UI all agree on the same list.
JUDGE_CRITERIA = ("specificity", "actionability", "novelty", "relevance")


class CriterionVerdict(BaseModel):
    """The judge's call on a single criterion, in blind A/B terms."""

    name: str = Field(description="one of JUDGE_CRITERIA")
    winner: str = Field(description='"A" | "B" | "tie"')
    rationale: str


class JudgeVerdict(BaseModel):
    """Raw judge output. Winners are in blind A/B terms — the JudgeAgent maps
    them back to metaphor/baseline so the judge never knows which is which."""

    winner: str = Field(description='overall winner: "A" | "B" | "tie"')
    criteria: list[CriterionVerdict] = Field(default_factory=list)
    reasoning: str = Field(description="2-4 sentences justifying the overall call")


class ComparisonResult(BaseModel):
    """De-anonymised outcome of one judge comparison.

    ``winner`` and each criterion winner are remapped from A/B to
    "metaphor" | "baseline" | "tie". ``order`` records which candidate was
    shown to the judge as "A" so a reviewer can audit for position bias.
    """

    winner: str = Field(description='"metaphor" | "baseline" | "tie"')
    criteria_winners: dict[str, str] = Field(
        default_factory=dict,
        description="criterion name -> 'metaphor' | 'baseline' | 'tie'",
    )
    reasoning: str = ""
    order: str = Field(
        default="metaphor_first",
        description='"metaphor_first" | "baseline_first" — audit trail',
    )
