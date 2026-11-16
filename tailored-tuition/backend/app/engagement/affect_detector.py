"""Rule-based affect detection from interaction signals.

Fixes vs. the spec:
  * Fatigue is checked first. In the spec, a tired student giving fast, short
    replies matched "boredom" first and got *harder* problems.
  * The declared thresholds (ERROR_FRUSTRATION, HELP_OVERWHELM) are actually
    used; the spec defined them and then hard-coded other numbers.
  * Latency is optional: it is unknown on the first turn or if the client does
    not report it, and latency rules are skipped instead of misfiring.
  * Boredom requires the student to be getting things right; fast, short,
    *wrong* answers are not boredom.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

AFFECTS = ("frustration", "boredom", "confusion", "flow", "fatigue", "neutral")

HELP_PATTERN = re.compile(
    r"\b(help|stuck|confus\w*|lost|no idea|i don'?t (get|understand|know)|hint|what does .* mean)\b", re.IGNORECASE
)


@dataclass
class AffectSignals:
    response_latency_seconds: float | None
    response_length_chars: int
    error_count_recent: int  # wrong attempts among the last 3 attempts
    same_error_repeated: int  # how many times the latest error tag occurred in a row
    help_requests_recent: int  # help requests in the last 5 student turns (incl. this one)
    session_duration_minutes: float
    correct_streak: int  # consecutive correct attempts


class AffectDetector:
    LATENCY_LONG = 45.0
    LATENCY_SHORT = 3.0
    LENGTH_SHORT = 15
    LENGTH_LONG = 200
    ERROR_FRUSTRATION = 2  # same mistake this many times in a row
    ERRORS_RECENT_FRUSTRATION = 3  # or this many wrong of the last 3
    HELP_CONFUSION = 2  # help requests that, with a long pause, signal confusion
    HELP_OVERWHELM = 3  # help requests that signal confusion on their own
    SESSION_FATIGUE = 25.0

    def detect(self, s: AffectSignals) -> str:
        latency = s.response_latency_seconds

        if s.session_duration_minutes > self.SESSION_FATIGUE and s.response_length_chars < self.LENGTH_SHORT:
            return "fatigue"

        if s.same_error_repeated >= self.ERROR_FRUSTRATION or s.error_count_recent >= self.ERRORS_RECENT_FRUSTRATION:
            return "frustration"

        if s.help_requests_recent >= self.HELP_OVERWHELM or (
            latency is not None and latency > self.LATENCY_LONG and s.help_requests_recent >= self.HELP_CONFUSION
        ):
            return "confusion"

        if (
            latency is not None
            and latency < self.LATENCY_SHORT
            and s.response_length_chars < self.LENGTH_SHORT
            and s.correct_streak >= 2
        ):
            return "boredom"

        if s.response_length_chars > self.LENGTH_LONG and s.error_count_recent <= 1 and s.help_requests_recent == 0:
            return "flow"
        if s.correct_streak >= 3 and s.help_requests_recent == 0:
            return "flow"

        return "neutral"


def is_help_request(text: str) -> bool:
    return bool(HELP_PATTERN.search(text))
