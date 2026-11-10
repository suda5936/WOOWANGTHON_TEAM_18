# syntax=docker/dockerfile:1
# 빌드 컨텍스트는 AI/ (`docker build -t ai AI`). 운영은 EC2에서 BE 옆에서 돈다.

FROM python:3.13.13-slim-bookworm
# uv 버전은 AI/uv.lock을 만든 uv와 맞춘다. PyPI에서 받아 레지스트리를 하나 더 타지 않는다.
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# 의존성 층: 소스가 바뀌어도 pyproject.toml과 uv.lock이 같으면 설치를 다시 하지 않는다.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY app ./app
USER nobody
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
