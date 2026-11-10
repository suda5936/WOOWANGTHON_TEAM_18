#!/usr/bin/env bash
# lint → typecheck → test, 첫 실패에서 멈춘다. BE/FE의 pnpm verify와 같은 역할. AI/ 안에서 ./verify.sh로 실행한다.
set -euo pipefail
cd "$(dirname "$0")"
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest -q
