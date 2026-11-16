"""Mastery-map payload for the frontend.

Fix vs. the spec: node statuses were mastered/learning/started/locked while the
summary counted mastered/learning/not_started, so the counts couldn't add up.
Statuses and summary keys now match. There is no "locked" state — students may
explore any concept (agency over gating); prerequisites are shown as edges.
`overall_progress` is the mean mastery across all concepts.
"""

from __future__ import annotations

from app.domain.knowledge_graph import KnowledgeGraph, status_for
from app.models import Mastery


def mastery_map(kg: KnowledgeGraph, rows: dict[str, Mastery]) -> dict:
    concepts = []
    counts = {"mastered": 0, "learning": 0, "started": 0, "not_started": 0}
    total_level = 0.0
    for c in kg.all():
        row = rows.get(c.id)
        level = row.level if row else 0.0
        status = status_for(level, row.attempts if row else 0)
        counts[status] += 1
        total_level += level
        concepts.append(
            {"id": c.id, "name": c.name, "chapter": c.chapter, "mastery": round(level, 3), "status": status}
        )
    n = len(concepts)
    return {
        "concepts": concepts,
        "connections": [{"from": a, "to": b} for a, b in kg.edges()],
        "summary": {"total_concepts": n, **counts, "overall_progress": round(total_level / n, 3) if n else 0.0},
    }
