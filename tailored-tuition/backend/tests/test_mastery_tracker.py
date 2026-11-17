from app.student.mastery_tracker import MasteryTracker, ema_update


def test_correct_increases_and_wrong_decreases():
    assert ema_update(0.3, True, 0.5) > 0.3
    assert ema_update(0.3, False, 0.5) < 0.3


def test_easy_questions_cannot_certify_mastery():
    level = 0.0
    for _ in range(100):
        level = ema_update(level, True, 0.1)
    assert level < 0.51  # capped near difficulty + margin, far below "mastered" (0.8)


def test_hard_questions_can_reach_mastery():
    level = 0.0
    for _ in range(30):
        level = ema_update(level, True, 0.7)
    assert level >= 0.8


def test_wrong_on_easy_costs_more_than_wrong_on_hard():
    assert ema_update(0.6, False, 0.1) < ema_update(0.6, False, 0.9)


def test_bounds():
    assert 0.0 <= ema_update(0.0, False, 1.0) <= 1.0
    assert ema_update(1.0, True, 1.0) == 1.0


def test_tracker_persists(db, onboarded_student):
    t = MasteryTracker(db)
    sid = onboarded_student.student["id"]
    assert t.get_level(sid, "sets_basics") == 0.0
    new = t.update(sid, "sets_basics", True, 0.5)
    db.commit()
    assert t.get_level(sid, "sets_basics") == new > 0
    assert t.all_levels(sid)["sets_basics"].attempts == 1
