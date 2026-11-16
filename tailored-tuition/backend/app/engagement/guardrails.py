"""Dark-pattern guardrails. Hard rules, deliberately not configurable.

Fix vs. the spec: plain substring matching on "classmates" would block the
Phase 2 study-buddy feature ("your AI classmate says...") and "others are"
matches innocent sentences. Patterns are now word-bounded and target the
*manipulative construction* (comparison, loss, urgency), not single words.
"""

from __future__ import annotations

import re

RULES = {
    "no_variable_rewards": "Progress must be deterministic and mastery-based. Never randomise rewards.",
    "no_loss_framing": "Never frame missed sessions as losses. 'Welcome back!' not 'You lost your streak!'",
    "no_leaderboards": "Progress is personal. Never compare students to each other.",
    "no_fomo": "Never use urgency or scarcity. 'Ready when you are' not 'Your classmates are ahead!'",
    "clear_exit_points": "Always suggest stopping when fatigue is detected. Never push 'one more'.",
    "mastery_not_xp": "Track and display concept mastery. Never award points, XP or badges.",
}

_DARK_PATTERNS = [
    r"\bdon'?t lose\b",
    r"\bfalling behind\b",
    r"\b(your|a|the) streak\b",
    r"\b(others|everyone else|your (friends|classmates|peers)) (are|is) (ahead|already|doing better)\b",
    r"\bahead of you\b",
    r"\bhurry\b",
    r"\blimited time\b",
    r"\byou'?ll miss\b",
    r"\blast chance\b",
    r"\bjust one more\b",
    r"\b(xp|points|badges?)\b",
]
_DARK_RE = re.compile("|".join(_DARK_PATTERNS), re.IGNORECASE)

GUARDRAIL_PROMPT = (
    "ENGAGEMENT ETHICS (non-negotiable): never compare the student with others; never use urgency, guilt, "
    "streaks, points, XP or badges; never pressure them to continue ('just one more'); when they seem tired, "
    "suggest stopping; praise effort and understanding specifically, not with generic hype."
)


def violations(message: str) -> list[str]:
    return [m.group(0) for m in _DARK_RE.finditer(message)]


def validate_notification(message: str) -> bool:
    """True if the message is free of dark patterns."""
    return not violations(message)


def session_advice(fatigue_detected: bool, session_minutes: float, turns: int, max_turns: int) -> str:
    """'suggest_stop' | 'gentle_check' | 'continue'."""
    if fatigue_detected or turns >= max_turns:
        return "suggest_stop"
    if session_minutes > 45 or turns >= int(max_turns * 0.8):
        return "gentle_check"
    return "continue"
