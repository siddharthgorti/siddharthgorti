"""Phase 2 stub: routes between tutor-only and tutor + classmate modes and
manages turn-taking in a multi-agent classroom."""


class SessionController:
    MODES = ("tutor", "tutor_and_buddy")

    def route(self, *_args, **_kwargs) -> str:
        raise NotImplementedError("Classroom modes are a Phase 2 feature")
