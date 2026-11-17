"""FastAPI application entry point.

Run (from backend/):  uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_profile, routes_progress, routes_quiz, routes_syllabus, routes_tutor
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
    init_db()
    get_knowledge_graph()  # validate the concept graph at startup (fail fast)
    if SAMPLES.is_dir():
        with SessionLocal() as db:
            n = seed_samples(db, get_knowledge_graph(), retriever, SAMPLES)
            if n:
                log.info("Seeded %d sample syllabus document(s)", n)
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
    for r in (routes_profile, routes_syllabus, routes_tutor, routes_quiz, routes_progress):
        app.include_router(r.router)

    @app.get("/api/health", response_model=HealthOut, tags=["meta"])
    def health():
        llm = get_llm()
        if llm.mode != "anthropic":  # offline stub or a local model: one model serves everything
            return {"status": "ok", "llm_mode": llm.mode, "model": llm.model, "quiz_model": llm.model}
        return {"status": "ok", "llm_mode": llm.mode, "model": settings.chat_model, "quiz_model": settings.quiz_model}

    return app


app = create_app()
