# Session B — AI agent — lessons

## Log

- 2026-11-10: Task pair created from the shared plan; the session starts here.
- 2026-11-10 B0 `feat/ai-scaffold`: `AI/` as a uv app (Python 3.13, FastAPI, uvicorn; dev: ruff, mypy strict, pytest, httpx2). `./verify.sh` runs ruff check → ruff format --check → mypy → pytest (2 passed). `docker build` + `GET /health` → `{"status":"ok"}` + runs as `nobody` checked locally — through a local-only copy of the Dockerfile that adds the session proxy's CA, because this container reaches the network only through that proxy. CI workflow `ai.yml` written, not run yet (runs on the fork PR).
  - Starlette warned that `httpx` with `TestClient` is deprecated → dev dependency is `httpx2`.
  - uv comes from PyPI (`pip install uv==0.11.32`), not `COPY --from=ghcr.io/astral-sh/uv`: GHCR blob downloads are blocked here, and one registry fewer is simpler anyway.
  - `.gitignore` entries for Python went into `AI/.gitignore`, not the root file, because the root file is outside both sessions' columns.

### Open questions for 현식

- B0-Q1: `.env.example` in `AI/` has only a comment; variables (`OPENAI_API_KEY`, `OPENAI_MODEL`, `AGENT_SHARED_TOKEN`, `BE_URL`) arrive with the features that read them. Default: keep it that way.
- B0-Q2: the AI server listens on port 8000 in the container. Default: 8000 (uvicorn's default); `AI_SERVER_URL` in BE will point at it.

### Needs from the other session

## Lessons

<filled when done>
