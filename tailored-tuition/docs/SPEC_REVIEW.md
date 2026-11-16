# Build Spec Review: Inconsistencies, Bugs and Gaps

Review of `tailored-tuition-build-spec.md` (Phase 1 MVP). Each item gives the problem, a concrete
example, what the implementation does instead, and a confidence level.

Severity: **High** = would produce wrong behaviour or block the build · **Medium** = contradiction
or ambiguity that forces a guess · **Low** = naming, structure or hygiene.

---

## A. Logic bugs in the spec's code

### A1. The Explainer persona is almost unreachable (High · certain)
The rule "Low Openness + Low Conscientiousness → The Explainer" can't fire in practice: nearly every
quiz option adds Openness or Conscientiousness. I enumerated all 4⁵ = 1,024 answer combinations, and
only 20 (2%) even keep both O ≤ 1 and C ≤ 1. Worse, the option that most clearly describes an
Explainer learner ("Someone breaking it down step by step") scores **+1 Conscientiousness**, which
pushes the student *away* from the Explainer.
**Implemented:** Explainer = high C and low O ("wants structure more than exploration"). All four
personas are now reachable: Explainer 34%, Mentor 27%, Challenger 24%, Coach 15% of combinations
(`tests/test_personality_model.py::test_every_persona_is_reachable`).

### A2. Raw OCEAN sums are biased toward Openness (High · certain)
Openness appears in 13 of the 20 options and Extraversion in only 6. Summing raw scores makes "high
Openness" the default for almost everyone. **Implemented:** each trait is divided by the maximum
score achievable for it.

### A3. Persona rules overlap, and "high" is undefined (Medium · certain)
"High O + High C → Challenger" and "High O + High E → Mentor" both match a student who is high on O,
C and E. "Ties broken by secondary traits" doesn't say how. **Implemented:** one affinity score per
persona; the highest wins; ties resolve in a fixed order with Coach first (the spec's default).

### A4. Affect detection order sends tired students harder problems (High · certain)
Boredom (fast and short replies) is checked before fatigue (long session and short replies). A
student 30 minutes in, replying "ok" quickly, is labelled *bored*, which triggers
`difficulty_adjustment: +1`. That is the opposite of the guardrail "always suggest stopping when
fatigue is detected". **Implemented:** fatigue is checked first. Boredom also now requires a streak
of correct answers, so fast *wrong* answers aren't treated as boredom.

### A5. Declared thresholds aren't used (Medium · certain)
`ERROR_FRUSTRATION = 2` and `HELP_OVERWHELM = 3` are defined, then the code hard-codes
`error_count_recent >= 3` and `help_requests_recent >= 2`. **Implemented:** all thresholds are named
constants that the rules actually use, and each is tested.

### A6. `SessionDesigner` never changes phase (High · certain)
`get_next_difficulty` returns `transition_after`, but nothing reads it or advances `session_phase`,
and `peak_achieved` is never set. In addition:
- `stretch` difficulty (`mastery + 0.1`) is unclamped and can exceed 1.0.
- An unknown phase falls through and returns `None`.
- What happens when fatigue strikes mid-stretch isn't defined.

**Implemented:** an explicit state machine (warm-up 2 → stretch 4 → peak 1 → end-high 1 → complete).
Difficulty is clamped to [0.1, 1.0] in every phase. Fatigue, or the student saying they want to stop,
jumps straight to end-high, so the session still ends on a success.

### A7. The "EMA" mastery rule isn't an EMA, and can be farmed (High · certain)
`+0.1·(1+d)` on correct and `−0.05·d` on wrong is additive, not an exponential moving average. With
easy questions (d = 0.1) a student reaches 1.0 ("fully mastered") after about 9 correct answers. A
wrong answer on an easy question costs almost nothing (−0.005).
**Implemented:** a true EMA toward an evidence target. Correct answers move toward
`min(1, d + 0.4)`, so easy questions alone can't push mastery past about 0.5; reaching 0.8 needs
problems of difficulty ≥ 0.4. Surprising results (a wrong answer on an easy question, a right answer
on a hard one) move the estimate more.

### A8. The mastery-map status vocabulary doesn't add up (Medium · certain)
Concept statuses are `mastered / learning / started / locked`, but the summary counts
`mastered / learning / not_started`. `started` and `locked` nodes appear in no count.
**Implemented:** `mastered / learning / started / not_started` in both places, with a test that the
counts sum to the total. `overall_progress` is defined as mean mastery.

### A9. Quiz difficulty bands have gaps (Low · certain)
Easy 0.0–0.3, Medium 0.4–0.6, Hard 0.7–1.0: a target of 0.35 or 0.65 fits no band.
**Implemented:** contiguous bands (< 0.35, < 0.7, ≥ 0.7).

### A10. The dark-pattern filter blocks your own Phase 2 feature (Medium · certain)
`"classmates"` is a banned substring, so "Your AI classmate has a question" (USP #2) would be blocked.
`"others are"` blocks innocent sentences.
**Implemented:** word-bounded patterns aimed at the manipulative construction ("your classmates are
ahead", "your streak", "just one more"), tested against both bad and benign messages.

## B. Contradictions between sections

### B1. "Never give the answer directly" vs. the Step 1 test (Medium · certain)
Step 1's acceptance test is "ask 'What is a set?', get a grounded answer". Step 2's rule 1 forbids
giving answers on the first attempt. The rule also conflicts with the Explainer persona, the
"confusion → worked example" adaptation, and the onboarding option "Tell me right away what went
wrong". **Implemented:** factual and definition questions are answered directly, followed by a
check-for-understanding question. Practice problems stay Socratic with graduated hints.

### B2. Streamlit vs. Next.js (Low · certain)
The weekend-demo section says to use Streamlit; the project tree and Step 7 say Next.js.
**Implemented:** Next.js only. Building a Streamlit UI first would be thrown away.

### B3. `strategizer.py` and `persona_manager.py` overlap (Low · likely)
Both are described as doing "strategy selection". **Implemented:** persona choice lives in
`persona_manager.py`; per-turn strategy changes come from `response_router.py`; `strategizer.py` is
a documented Phase 2 hook (for example, a bandit that learns which strategies raise mastery).

### B4. "BKT or FSRS-based tracing" (Low · certain)
FSRS is a spaced-repetition *scheduler* (when to review), not a knowledge-tracing model (what the
student knows). They complement each other rather than being alternatives. This is noted in
`knowledge_tracing.py`, which includes a reference BKT update.

### B5. `knowledge_graph.get_next_unlockable(student_id, …)` breaks the layering (Low · certain)
A Layer-1 domain object taking a `student_id` has to reach into Layer-2 student state.
**Implemented:** the graph takes a `mastery` dict as an argument and stays pure.

### B6. `guardrails.py` is missing from the project tree (Low · certain)
It's specified in the guardrails section but absent from the structure. It is now at
`engagement/guardrails.py`.

### B7. "Locked" concepts vs. student agency (Medium · judgement call)
The mastery map shows locked nodes, while the onboarding offers "Flexible: I want to explore". Hard
gating also contradicts the Mentor persona. **Implemented:** nothing is locked. Prerequisites show
as edges, and the end-of-session teaser *recommends* the next concept.

## C. Things the spec leaves undefined (the build had to decide)

### C1. Where does "correct / error" come from in a chat? (High · certain)
The mastery tracker needs `correct` and the affect detector needs `error_count_recent` and
`same_error_repeated`, but a chat message has no answer key. **Implemented:** one structured LLM call
returns both the reply *and* an assessment of the student's message (`kind`, `correct`, `error_tag`,
`problem_completed`). Affect is computed before that call, so error-based signals lag one turn; the
trade-off is documented in `tutor_engine.py`.

### C2. How is a "problem" counted for phase transitions? (Medium · certain)
**Implemented:** `problem_completed` from the assessment: either the student solved it, or the tutor
has walked through the full solution. Peak counts as "achieved" only if the student solved it.

### C3. Response latency (Medium · certain)
It isn't defined who measures it or from when. **Implemented:** the client measures from when the
tutor message renders to when the student hits send. It is optional, and the latency rules are
skipped when it's missing.

### C4. Knowledge-graph prerequisites can't be extracted from a PDF (High · likely)
Step 1 says to "build simple knowledge graph: topic → prerequisites" from the upload, without saying
how. Reliable automatic prerequisite extraction is an open research problem. **Implemented:** a
hand-curated graph of 33 concepts across the 14 chapters of the rationalised NCERT Class 11 book
(`app/data/ncert_math_11.json`), with uploads tagged to concepts by keyword. Treat the chapter list
as ~85% confidence: please check it against the current NCERT edition.

### C5. Difficulty adjustment units (Low · certain)
`difficulty_adjustment: ±1` has no unit. **Implemented:** one step = 0.15, bounded to ±2 steps.

## D. Risks the spec doesn't mention

1. **Children's data (High · likely).** Class 11 students are typically 15–17. India's DPDP Act 2023
   requires *verifiable* parental consent to process children's data and restricts behavioural
   monitoring of children. Affect detection and "personality" profiling arguably fall under that.
   The MVP adds a required guardian-consent checkbox; a real product needs a proper verification
   flow and legal review before launch. I'm confident the Act applies to under-18s; how it applies
   to affect detection specifically needs a lawyer.
2. **Five questions can't measure Big Five personality (High · certain).** Validated short
   instruments use 10+ items, and these questions measure learning *preferences*. The app therefore
   frames the result as "how you like to learn" and lets the student switch persona at any time.
   Consider dropping OCEAN and mapping answers to personas directly; it's simpler and more honest.
3. **PDF maths extraction (High · certain).** pdfplumber/PyPDF2 flatten fractions, superscripts and
   matrices (for example, $x^2$ becomes "x2"). Retrieval still works on the prose, but grounding on
   equations is weak. A LaTeX/OCR step (Nougat, Mathpix) is a Phase 2 item.
4. **LLM-generated answer keys can be wrong (High · likely).** Quiz items are structurally validated
   and generated at higher effort, and grading is deterministic. Wrong *keys* remain possible. Add a
   second-pass solver check, or a curated question bank, before high-stakes use.
5. **Hosting.** SQLite and a local vector store on Render/Railway free tiers sit on ephemeral disks:
   data is lost on redeploy. Use Postgres from the first deployment.
6. **Copyright.** NCERT textbooks are © NCERT. Use your own notes or licensed content for anything
   public. The bundled sample notes are original writing.

## E. Stack choices I changed (and why)

| Spec | Built | Why |
|---|---|---|
| Claude Sonnet 4 / GPT-4o-mini | `claude-sonnet-5-5` (configurable) | Sonnet 4 is outdated; this is the current Sonnet. GPT-4o-mini is weak at multi-step maths. |
| LangChain/LlamaIndex | Anthropic SDK directly | The pipeline is one retrieval plus one structured call; a framework adds dependencies without removing code. |
| ChromaDB | In-process BM25 behind a `Retriever` interface | No embedding-model download. Exact maths vocabulary ("nCr", "discriminant") suits lexical search, and it's swappable later. |
| NetworkX | A ~100-line DAG class | Topological order and cycle checks are all the MVP needs. |
| Free-text LLM replies | Structured outputs (`reply` + `assessment`) | This is what makes mastery and affect tracking possible (C1). |
| `backend/main.py` | `backend/app/main.py` (a package) | Clean absolute imports and testability. |
