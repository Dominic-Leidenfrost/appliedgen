"""Load seed domain YAML files from examples/domains/.

Each YAML contains: name, display, description, vocabulary,
archetypal_entities, typical_relations. The Transformer uses these as
style hints — they shape the domain without locking in specific content.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

_DOMAINS_DIR = Path(__file__).resolve().parents[5] / "examples" / "domains"


@dataclass
class DomainSeed:
    name: str
    display: str
    description: str
    vocabulary: list[str]
    archetypal_entities: dict[str, list[str]]
    typical_relations: list[str]

    def as_style_hint(self) -> str:
        """Build a concise style-hint string for the Transformer prompt."""
        vocab_preview = ", ".join(self.vocabulary[:8])
        return (
            f"Domain: {self.display}\n"
            f"Setting: {self.description.strip()}\n"
            f"Vocabulary: {vocab_preview}\n"
            f"Typical relations: {'; '.join(self.typical_relations[:3])}"
        )


def load_all() -> list[DomainSeed]:
    """Return all seed domains found in examples/domains/."""
    seeds: list[DomainSeed] = []
    for path in sorted(_DOMAINS_DIR.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "name" not in data:
            continue
        seeds.append(
            DomainSeed(
                name=data["name"],
                display=data.get("display", data["name"]),
                description=data.get("description", ""),
                vocabulary=data.get("vocabulary", []),
                archetypal_entities=data.get("archetypal_entities", {}),
                typical_relations=data.get("typical_relations", []),
            )
        )
    return seeds


def pick_diverse(n: int = 3, rng: random.Random | None = None) -> list[DomainSeed]:
    """Pick n seeds that are structurally spread across the pool.

    Simple heuristic: divide seeds into n roughly equal buckets and pick one
    per bucket. The pool is sorted alphabetically so adjacent seeds tend to be
    thematically distant (e.g. ecosystem / fluid_dynamics / garden are all
    'natural', but separated from heist / kitchen / medieval / pirate /
    sports / video_game). Randomise within each bucket.
    """
    all_seeds = load_all()
    if len(all_seeds) <= n:
        return all_seeds
    rng = rng or random.Random()
    bucket_size = len(all_seeds) // n
    chosen: list[DomainSeed] = []
    for i in range(n):
        start = i * bucket_size
        end = start + bucket_size if i < n - 1 else len(all_seeds)
        chosen.append(rng.choice(all_seeds[start:end]))
    return chosen
