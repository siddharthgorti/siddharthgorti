from app.engagement.session_designer import PHASE_PLAN, FlowState, SessionDesigner


def run_through(designer, n):
    for _ in range(n):
        designer.record_problem_completed(solved_independently=True)


def test_full_flow_reaches_complete():
    d = SessionDesigner(FlowState())
    seen = [d.state.phase]
    for _ in range(sum(n for _, n in PHASE_PLAN)):
        d.record_problem_completed(True)
        if d.state.phase != seen[-1]:
            seen.append(d.state.phase)
    assert seen == ["warmup", "stretch", "peak", "end_high", "complete"]
    assert d.state.peak_achieved


def test_peak_not_achieved_if_solution_was_walked_through():
    d = SessionDesigner(FlowState(phase="peak"))
    d.record_problem_completed(solved_independently=False)
    assert not d.state.peak_achieved
    assert d.state.phase == "end_high"


def test_difficulty_ordering_and_clamping():
    for mastery in (0.0, 0.5, 1.0):
        values = {}
        for phase in ("warmup", "stretch", "peak", "end_high"):
            values[phase] = SessionDesigner(FlowState(phase=phase)).target_difficulty(mastery)
            assert 0.1 <= values[phase] <= 1.0
        assert values["end_high"] <= values["warmup"] <= values["stretch"] <= values["peak"]


def test_wrap_up_jumps_to_end_high():
    d = SessionDesigner(FlowState(phase="stretch", problems_in_phase=2))
    d.request_wrap_up()
    assert d.state.phase == "end_high" and d.state.wrap_requested
    d.record_problem_completed(True)
    assert d.state.phase == "complete"


def test_affect_offset_is_bounded():
    d = SessionDesigner(FlowState(phase="stretch"))
    for _ in range(10):
        d.apply_affect(+1)
    assert d.state.difficulty_offset == 0.3
    for _ in range(10):
        d.apply_affect(-1)
    assert d.state.difficulty_offset == -0.3


def test_state_roundtrip_ignores_unknown_keys():
    s = FlowState(phase="peak", problems_in_phase=1)
    assert FlowState.from_dict({**s.to_dict(), "junk": 1}) == s


def test_complete_is_terminal():
    d = SessionDesigner(FlowState(phase="complete"))
    run_through(d, 3)
    assert d.state.phase == "complete"
