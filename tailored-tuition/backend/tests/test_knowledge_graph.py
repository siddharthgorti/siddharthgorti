import pytest

from app.domain.knowledge_graph import Concept, KnowledgeGraph, get_knowledge_graph, status_for


def test_bundled_graph_is_valid_and_ordered():
    kg = get_knowledge_graph()
    concepts = kg.all()
    assert len(concepts) >= 30
    position = {c.id: i for i, c in enumerate(concepts)}
    for c in concepts:
        for p in c.prerequisites:
            if kg.get(p).chapter == c.chapter:
                assert position[p] < position[c.id]


def test_rejects_cycles_and_unknown_prereqs():
    a = Concept("a", "A", 1, ("b",), "", ())
    b = Concept("b", "B", 1, ("a",), "", ())
    with pytest.raises(ValueError, match="cycle"):
        KnowledgeGraph([a, b])
    with pytest.raises(ValueError, match="unknown"):
        KnowledgeGraph([Concept("a", "A", 1, ("zzz",), "", ())])


def test_next_unlockable_prefers_dependents_of_current():
    kg = get_knowledge_graph()
    nxt = kg.next_unlockable("sets_basics", {"sets_basics": 0.9})
    assert nxt[0].id in {"set_operations", "cartesian_product"}
    assert all(c.id != "sets_basics" for c in nxt)


def test_next_unlockable_requires_other_prereqs_mastered():
    kg = get_knowledge_graph()
    ids = {c.id for c in kg.next_unlockable("complex_algebra", {})}
    assert "argand_plane" not in ids  # also needs trig_functions
    assert "quadratic_complex_roots" in ids


def test_match_concept():
    kg = get_knowledge_graph()
    assert kg.match_concept("The union and intersection of two sets, and De Morgan") == "set_operations"
    assert kg.match_concept("nothing relevant here at all") is None


@pytest.mark.parametrize(
    ("level", "attempts", "status"),
    [(0.0, 0, "not_started"), (0.1, 1, "started"), (0.0, 2, "started"), (0.5, 3, "learning"), (0.85, 9, "mastered")],
)
def test_status(level, attempts, status):
    assert status_for(level, attempts) == status
