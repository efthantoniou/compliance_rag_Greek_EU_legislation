"""Resolve EUROVOC concept IDs to human-readable descriptors.

The multi_eurlex dataset tags each document with numeric EUROVOC concept IDs at
three granularities (level_1 domains, level_2 microthesauri, level_3 concepts).
`eurovoc_descriptors.json` (bundled) maps every level-1/2/3 ID to its Greek and
English descriptor, so the UI can show names instead of opaque numbers.
"""

import json
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("eurovoc_descriptors.json")


@lru_cache(maxsize=1)
def _data() -> dict:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def concept(concept_id: str) -> dict:
    """Resolve one ID to `{"id", "el", "en"}`.

    Unknown IDs fall back to the raw ID for both names, so nothing is dropped.
    """
    entry = _data()["concepts"].get(concept_id)
    if not entry:
        return {"id": concept_id, "el": concept_id, "en": concept_id}
    return {"id": concept_id, "el": entry["el"] or concept_id, "en": entry["en"] or concept_id}


def concepts(ids: list[str]) -> list[dict]:
    return [concept(i) for i in ids]


def level_1_options() -> list[dict]:
    """The 21 level-1 domains, resolved and sorted by Greek descriptor."""
    ids = _data()["levels"]["level_1"]
    return sorted((concept(i) for i in ids), key=lambda c: c["el"])
