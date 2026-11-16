import pytest

from app.engagement.guardrails import session_advice, validate_notification


@pytest.mark.parametrize(
    "msg",
    [
        "Don't lose your streak!",
        "You're falling behind",
        "Your classmates are ahead of you",
        "Hurry, limited time offer",
        "Last chance to practise today",
        "Just one more problem?",
        "You earned 50 XP",
    ],
)
def test_blocks_dark_patterns(msg):
    assert not validate_notification(msg)


@pytest.mark.parametrize(
    "msg",
    [
        "Welcome back! Ready when you are.",
        "Your AI classmate has a question about sets.",  # the spec's substring rule blocked this
        "Others are welcome to join the study group later.",
        "Great work on unions today.",
    ],
)
def test_allows_healthy_messages(msg):
    assert validate_notification(msg)


def test_session_advice():
    assert session_advice(True, 5, 3, 50) == "suggest_stop"
    assert session_advice(False, 50, 3, 50) == "gentle_check"
    assert session_advice(False, 5, 40, 50) == "gentle_check"
    assert session_advice(False, 5, 50, 50) == "suggest_stop"
    assert session_advice(False, 5, 3, 50) == "continue"
