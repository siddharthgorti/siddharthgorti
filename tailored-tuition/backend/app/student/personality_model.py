"""Onboarding quiz -> trait profile -> tutor persona.

Honest framing: five forced-choice questions cannot measure Big Five
personality. What they *can* capture is learning preferences. We keep the OCEAN
vocabulary from the spec as an internal scoring layer, but the result is shown
to students as "how you like to learn", the student can override the match, and
nothing here is used for anything except choosing a tutoring style.

Fixes vs. the original spec:
  * Raw sums are biased toward Openness (it appears in most options), so each
    trait is normalised by the maximum score achievable for it.
  * "Low Openness + Low Conscientiousness -> Explainer" was effectively
    unreachable (almost every option adds O or C) and contradicted the quiz,
    where "break it down step by step" scores C. The Explainer is now the match
    for learners who want structure (high C) more than exploration (low O).
  * The rules overlapped (O+C vs O+E). Each persona now has one affinity score;
    the highest wins and ties resolve in a fixed order with The Coach first.
"""

from __future__ import annotations

from dataclasses import dataclass

TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

ONBOARDING_QUESTIONS: list[dict] = [
    {
        "id": "motivation_style",
        "question": "When you're struggling with a tough problem, what helps you most?",
        "options": [
            {"text": "Someone cheering me on and saying I can do it", "scores": {"agreeableness": 1, "neuroticism": 1}},
            {"text": "Someone challenging me to think harder", "scores": {"openness": 1, "conscientiousness": 1}},
            {"text": "Someone breaking it down step by step", "scores": {"conscientiousness": 1}},
            {"text": "Someone showing me why it matters in real life", "scores": {"openness": 1, "extraversion": 1}},
        ],
    },
    {
        "id": "pace_preference",
        "question": "How do you prefer to learn something new?",
        "options": [
            {"text": "Thorough explanation with every detail", "scores": {"conscientiousness": 1, "neuroticism": 0.5}},
            {"text": "Quick summary, then I'll figure out the rest", "scores": {"openness": 1, "extraversion": 0.5}},
            {"text": "Lots of examples to practise with", "scores": {"conscientiousness": 1}},
            {"text": "Discussion and debate about the concept", "scores": {"openness": 1, "extraversion": 1}},
        ],
    },
    {
        "id": "engagement_style",
        "question": "What makes a topic interesting to you?",
        "options": [
            {"text": "Seeing how it applies to real-world problems", "scores": {"openness": 1, "extraversion": 0.5}},
            {
                "text": "Understanding the underlying patterns and logic",
                "scores": {"openness": 1, "conscientiousness": 0.5},
            },
            {"text": "Solving progressively harder challenges", "scores": {"conscientiousness": 1, "openness": 0.5}},
            {"text": "Connecting it to things I already know", "scores": {"agreeableness": 0.5, "neuroticism": 0.5}},
        ],
    },
    {
        "id": "feedback_preference",
        "question": "When you make a mistake, what do you prefer?",
        "options": [
            {"text": "Tell me right away what went wrong", "scores": {"conscientiousness": 1}},
            {"text": "Ask me questions so I find the mistake myself", "scores": {"openness": 1}},
            {"text": "Show me a similar problem done correctly", "scores": {"agreeableness": 0.5, "neuroticism": 0.5}},
            {"text": "Let me try again before pointing it out", "scores": {"openness": 0.5, "extraversion": 0.5}},
        ],
    },
    {
        "id": "structure_need",
        "question": "How do you like your study sessions?",
        "options": [
            {"text": "Structured with clear goals and a plan", "scores": {"conscientiousness": 1, "neuroticism": 0.5}},
            {"text": "Flexible — I want to explore what interests me", "scores": {"openness": 1, "extraversion": 0.5}},
            {
                "text": "A mix — some structure but room to go deeper",
                "scores": {"openness": 0.5, "conscientiousness": 0.5},
            },
            {"text": "Whatever keeps me focused and motivated", "scores": {"agreeableness": 0.5, "neuroticism": 1}},
        ],
    },
]

# Order matters: it is the tie-break order (Coach is the spec's default).
PERSONA_ORDER = ("coach", "challenger", "explainer", "mentor")


@dataclass
class PersonaMatch:
    persona: str
    traits: dict[str, float]  # normalised 0..1
    affinities: dict[str, float]
    rationale: str


class InvalidAnswersError(ValueError):
    pass


def _max_per_trait() -> dict[str, float]:
    return {t: sum(max(o["scores"].get(t, 0) for o in q["options"]) for q in ONBOARDING_QUESTIONS) for t in TRAITS}


def score_answers(answers: dict[str, int]) -> dict[str, float]:
    """answers: question_id -> option index. Returns normalised trait scores."""
    by_id = {q["id"]: q for q in ONBOARDING_QUESTIONS}
    missing = set(by_id) - set(answers)
    if missing:
        raise InvalidAnswersError(f"Missing answers for: {', '.join(sorted(missing))}")
    raw = dict.fromkeys(TRAITS, 0.0)
    for qid, idx in answers.items():
        q = by_id.get(qid)
        if q is None:
            raise InvalidAnswersError(f"Unknown question: {qid}")
        if not 0 <= idx < len(q["options"]):
            raise InvalidAnswersError(f"Invalid option {idx} for {qid}")
        for trait, val in q["options"][idx]["scores"].items():
            raw[trait] += val
    maxima = _max_per_trait()
    return {t: round(raw[t] / maxima[t], 3) if maxima[t] else 0.0 for t in TRAITS}


def persona_affinities(tr: dict[str, float]) -> dict[str, float]:
    return {
        "coach": (tr["agreeableness"] + tr["neuroticism"]) / 2,
        "challenger": (tr["openness"] + tr["conscientiousness"]) / 2,
        "explainer": (tr["conscientiousness"] + (1 - tr["openness"])) / 2,
        "mentor": (tr["openness"] + tr["extraversion"]) / 2,
    }


_RATIONALE = {
    "coach": "You told us encouragement and steady support help you most, so your tutor will be warm and patient and celebrate your progress.",
    "challenger": "You enjoy being pushed and like understanding the logic, so your tutor will ask probing questions and raise the bar as you go.",
    "explainer": "You like clear structure and worked steps, so your tutor will explain things methodically and check understanding at each step.",
    "mentor": "You're curious and like discussing ideas and real-world uses, so your tutor will connect maths to the bigger picture.",
}


def match_persona(answers: dict[str, int]) -> PersonaMatch:
    traits = score_answers(answers)
    aff = persona_affinities(traits)
    best = max(PERSONA_ORDER, key=lambda p: (round(aff[p], 6), -PERSONA_ORDER.index(p)))
    return PersonaMatch(persona=best, traits=traits, affinities=aff, rationale=_RATIONALE[best])


def public_questions() -> list[dict]:
    """Questions without the scoring keys (scores never go to the client)."""
    return [
        {
            "id": q["id"],
            "question": q["question"],
            "options": [{"index": i, "text": o["text"]} for i, o in enumerate(q["options"])],
        }
        for q in ONBOARDING_QUESTIONS
    ]
