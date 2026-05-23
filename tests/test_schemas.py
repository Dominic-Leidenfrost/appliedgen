"""Smoke tests that the Pydantic schemas validate and round-trip through JSON."""

from metaphor_machine.core.schemas import (
    Entity,
    Mapping,
    MetaphorSpec,
    Move,
    ProblemSpec,
    Relation,
    Solution,
)


def test_problemspec_roundtrip() -> None:
    p = ProblemSpec(
        raw_user_text="too many priorities",
        summary="tiny team, too much work",
        entities=[Entity(name="team", role="actor", attributes=["small"])],
        relations=[Relation(source="team", target="projects", kind="overwhelmed_by")],
        constraints=["4 people"],
        goals=["ship the right things"],
        tensions=["speed vs. quality"],
        unknowns=["which projects can be cut"],
    )
    p2 = ProblemSpec.model_validate_json(p.model_dump_json())
    assert p2.summary == p.summary
    assert p2.entities[0].name == "team"


def test_metaphorspec_roundtrip() -> None:
    m = MetaphorSpec(
        domain="pirate adventure",
        domain_intro="A ship with a small crew chasing too many islands.",
        mappings=[
            Mapping(original="team", metaphor="ship's crew", fidelity=0.8, leak="ships can grow"),
        ],
    )
    m2 = MetaphorSpec.model_validate_json(m.model_dump_json())
    assert m2.domain == "pirate adventure"


def test_move_and_solution() -> None:
    move = Move(actor="Captain Reyes", action="set course for nearest island", obstacle="storm")
    sol = Solution(
        metaphor_idea="anchor at one island first",
        original_domain_translation="commit to one project for 2 weeks before reassessing",
        confidence=0.7,
        caveats=["islands are static; projects are not"],
    )
    assert move.obstacle == "storm"
    assert sol.caveats
