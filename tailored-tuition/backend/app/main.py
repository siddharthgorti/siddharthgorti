"""FastAPI application entry point.

Run (from backend/):  uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_auth,
    routes_guardian,
    routes_profile,
    routes_progress,
    routes_quiz,
    routes_syllabus,
    routes_tutor,
)
from app.api.schemas import HealthOut
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.domain.ingest import seed_samples
from app.domain.knowledge_graph import get_knowledge_graph
from app.domain.rag_pipeline import retriever
from app.llm.client import get_llm

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "sample_syllabi"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("tailored_tuition")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    problems = settings.production_problems()
    if problems:
        # Refuse to run in production with settings that would expose children's data.
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
    init_db()
    get_knowledge_graph()  # validate the concept graph at startup (fail fast)
    if SAMPLES.is_dir():
        with SessionLocal() as db:
            n = seed_samples(db, get_knowledge_graph(), retriever, SAMPLES)
            if n:
                log.info("Seeded %d sample syllabus document(s)", n)
    if settings.seed_demo_accounts and settings.app_env == "development":
        from app.demo_seed import seed_demo_accounts

        with SessionLocal() as db:
            seed_demo_accounts(db, settings)
    llm = get_llm()
    if llm.mode == "offline":
        log.info("LLM mode: offline (canned demo replies; add ANTHROPIC_API_KEY or start Ollama for real tutoring)")
    elif llm.mode == "ollama":
        log.info("LLM mode: local model via Ollama (%s)", llm.model)
    else:
        settings = get_settings()
        log.info("LLM mode: %s (chat: %s, quiz: %s)", llm.mode, settings.chat_model, settings.quiz_model)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Tailored Tuition API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Reject oversized bodies BEFORE they are read: multipart parsing would
    # otherwise spool the whole upload to disk before the route's own size check.
    max_body = (settings.max_upload_mb + 1) * 1024 * 1024
    json_max_body = 64 * 1024

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            is_upload = request.url.path == "/api/syllabus/upload"
            limit = max_body if is_upload else json_max_body
            length = request.headers.get("content-length")
            if length is None:
                if is_upload:  # chunked uploads have no declared size to check
                    return JSONResponse({"detail": "Upload size must be declared (Content-Length)."}, 411)
            elif not length.isdigit() or int(length) > limit:
                return JSONResponse({"detail": f"Request too large (limit {limit // 1024} KB)."}, 413)
        return await call_next(request)

    # CSRF: unsafe requests must carry a custom header. A page on another site
    # cannot add one without a CORS preflight, which this API never approves
    # for other origins, so forged cross-site form posts and fetches fail.
    @app.middleware("http")
    async def require_csrf_header(request: Request, call_next):
        if (
            request.method in ("POST", "PUT", "PATCH", "DELETE")
            and request.url.path.startswith("/api/")
            and request.headers.get("x-tt-csrf") != "1"
        ):
            return JSONResponse({"detail": "Missing security header. Please reload the page."}, 403)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def readable_validation_error(_: Request, exc: RequestValidationError):
        # FastAPI's default is a nested list; the frontend shows `detail` as text.
        parts = []
        for err in exc.errors():
            field = ".".join(str(x) for x in err.get("loc", []) if x not in ("body", "query", "path"))
            parts.append(f"{field}: {err.get('msg', 'invalid')}" if field else err.get("msg", "invalid"))
        return JSONResponse({"detail": "; ".join(parts) or "Invalid request."}, 422)

    for r in (
        routes_auth,
        routes_guardian,
        routes_profile,
        routes_syllabus,
        routes_tutor,
        routes_quiz,
        routes_progress,
    ):
        app.include_router(r.router)

    @app.get("/api/health", response_model=HealthOut, tags=["meta"])
    def health():
        llm = get_llm()
        if llm.mode != "anthropic":  # offline stub or a local model: one model serves everything
            return {"status": "ok", "llm_mode": llm.mode, "model": llm.model, "quiz_model": llm.model}
        return {"status": "ok", "llm_mode": llm.mode, "model": settings.chat_model, "quiz_model": settings.quiz_model}

    return app


app = create_app()
