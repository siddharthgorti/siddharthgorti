# Backend image: FastAPI + uvicorn, runs as a non-root user.
# Build context is the repository root (see docker-compose*.yml).
#
# Base image is pinned to a Python minor version and Debian release. For fully
# reproducible builds, pin by digest once you have pulled it:
#   docker pull python:3.13-slim-bookworm && docker inspect --format '{{index .RepoDigests 0}}' python:3.13-slim-bookworm
#   FROM python:3.13-slim-bookworm@sha256:<digest>
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend
RUN useradd --create-home --uid 10001 appuser

# Dependencies first, so code changes don't reinstall them.
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Application code (tests, evals, local data and .env files are excluded by .dockerignore).
COPY backend/ .
# Bundled sample syllabus notes, read at /app/data/sample_syllabi on first start.
COPY data/sample_syllabi /app/data/sample_syllabi
RUN mkdir -p data && chown appuser:appuser data

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"]

# One worker on purpose: login lockouts and the retrieval index are kept in process memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]
