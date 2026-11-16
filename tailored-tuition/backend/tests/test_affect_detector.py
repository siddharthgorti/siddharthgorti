import pytest

from app.engagement.affect_detector import AffectDetector, AffectSignals, is_help_request


def sig(**kw):
    base = dict(
        response_latency_seconds=10.0,
        response_length_chars=60,
        error_count_recent=0,
        same_error_repeated=0,
        help_requests_recent=0,
        session_duration_minutes=5.0,
        correct_streak=0,
    )
    base.update(kw)
    return AffectSignals(**base)


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        (sig(same_error_repeated=2), "frustration"),
        (sig(error_count_recent=3), "frustration"),
        (sig(response_latency_seconds=60, help_requests_recent=2), "confusion"),
        (sig(help_requests_recent=3), "confusion"),
        (sig(response_latency_seconds=1.5, response_length_chars=3, correct_streak=2), "boredom"),
        (sig(session_duration_minutes=30, response_length_chars=4), "fatigue"),
        (sig(response_length_chars=250), "flow"),
        (sig(correct_streak=3), "flow"),
        (sig(), "neutral"),
    ],
)
def test_states(signals, expected):
    assert AffectDetector().detect(signals) == expected


def test_fatigue_beats_boredom():
    # The spec's ordering sent a tired student fast, short replies -> "boredom" -> harder problems.
    s = sig(session_duration_minutes=40, response_latency_seconds=1.0, response_length_chars=3, correct_streak=2)
    assert AffectDetector().detect(s) == "fatigue"


def test_fast_wrong_answers_are_not_boredom():
    s = sig(response_latency_seconds=1.0, response_length_chars=3, correct_streak=0, error_count_recent=1)
    assert AffectDetector().detect(s) != "boredom"


def test_unknown_latency_skips_latency_rules():
    assert (
        AffectDetector().detect(sig(response_latency_seconds=None, response_length_chars=3, correct_streak=5)) == "flow"
    )


@pytest.mark.parametrize("text", ["I'm stuck", "can you give me a hint", "I don't understand this", "help!"])
def test_help_requests(text):
    assert is_help_request(text)


def test_not_help():
    assert not is_help_request("x = 4")
