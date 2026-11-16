"""Curated concept graph (concept -> prerequisites) for the syllabus.

Prerequisites cannot be reliably *extracted* from a PDF, so the MVP ships a
hand-curated graph for NCERT Class 11 Mathematics. The graph is pure domain
data: it never reads student state. Callers pass mastery in, which keeps the
domain layer independent of the student layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "ncert_math_11.json"

MASTERED = 0.8
LEARNING = 0.4


@dataclass(frozen=True)
class Concept:
    id: str
    name: str
    chapter: int
    prerequisites: tuple[str, ...]
    description: str
    keywords: tuple[str, ...]


class KnowledgeGraph:
    def __init__(self, concepts: list[Concept]):
        self._by_id = {c.id: c for c in concepts}
        if len(self._by_id) != len(concepts):
            raise ValueError("duplicate concept ids")
        for c in concepts:
            for p in c.prerequisites:
                if p not in self._by_id:
                    raise ValueError(f"{c.id}: unknown prerequisite {p}")
        self._order = self._topological_order()  # also rejects cycles

    @classmethod
    def from_file(cls, path: Path = DATA_FILE) -> KnowledgeGraph:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            [
                Concept(
                    id=c["id"],
                    name=c["name"],
                    chapter=c["chapter"],
                    prerequisites=tuple(c["prerequisites"]),
                    description=c["description"],
                    keywords=tuple(k.lower() for k in c["keywords"]),
                )
                for c in raw["concepts"]
            ]
        )

    # -- queries -------------------------------------------------------------
    def get(self, concept_id: str) -> Concept | None:
        return self._by_id.get(concept_id)

    def all(self) -> list[Concept]:
        """Concepts ordered by chapter, then prerequisite depth."""
        depth = self._depths()
        return sorted(self._by_id.values(), key=lambda c: (c.chapter, depth[c.id], c.id))

    def edges(self) -> list[tuple[str, str]]:
        """(prerequisite, dependent) pairs."""
        return [(p, c.id) for c in self.all() for p in c.prerequisites]

    def dependents(self, concept_id: str) -> list[Concept]:
        return [c for c in self.all() if concept_id in c.prerequisites]

    def next_unlockable(self, current_id: str, mastery: dict[str, float]) -> list[Concept]:
        """Unmastered concepts whose prerequisites are all mastered (or are the
        current concept, which the student just worked on). Direct dependents of
        the current concept come first, then the rest in syllabus order."""

        def ready(c: Concept) -> bool:
            return all(p == current_id or mastery.get(p, 0.0) >= MASTERED for p in c.prerequisites)

        candidates = [c for c in self.all() if c.id != current_id and mastery.get(c.id, 0.0) < MASTERED and ready(c)]
        return sorted(candidates, key=lambda c: (current_id not in c.prerequisites, c.chapter))

    def match_concept(self, text: str) -> str | None:
        """Best concept for a chunk of text by keyword hits (None if no hits)."""
        lowered = text.lower()
        best, best_score = None, 0
        for c in self._by_id.values():
            score = sum(lowered.count(k) for k in c.keywords)
            if score > best_score:
                best, best_score = c.id, score
        return best

    # -- internals -----------------------------------------------------------
    def _topological_order(self) -> list[str]:
        visiting, done, order = set(), set(), []

        def visit(cid: str) -> None:
            if cid in done:
                return
            if cid in visiting:
                raise ValueError(f"cycle at {cid}")
            visiting.add(cid)
            for p in self._by_id[cid].prerequisites:
                visit(p)
            visiting.discard(cid)
            done.add(cid)
            order.append(cid)

        for cid in self._by_id:
            visit(cid)
        return order

    def _depths(self) -> dict[str, int]:
        depth: dict[str, int] = {}
        for cid in self._order:
            prereqs = self._by_id[cid].prerequisites
            depth[cid] = 1 + max((depth[p] for p in prereqs), default=-1)
        return depth


def status_for(level: float, attempts: int) -> str:
    if level >= MASTERED:
        return "mastered"
    if level >= LEARNING:
        return "learning"
    if attempts > 0 or level > 0:
        return "started"
    return "not_started"


@lru_cache
def get_knowledge_graph() -> KnowledgeGraph:
    return KnowledgeGraph.from_file()
