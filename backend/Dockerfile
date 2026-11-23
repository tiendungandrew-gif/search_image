FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM python:3.12.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 \
    PATH="/srv/backend/.venv/bin:$PATH" RUFF_CACHE_DIR=/tmp/ruff-cache
WORKDIR /srv
ARG INSTALL_ML=false
ARG INSTALL_EVALUATION=false
COPY backend/pyproject.toml backend/uv.lock backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    research_extra=""; if [ "$INSTALL_EVALUATION" = true ]; then research_extra="--extra evaluation"; fi; \
    if [ "$INSTALL_ML" = true ]; then uv sync --project backend --frozen --extra dev --extra ml $research_extra --no-install-project --no-managed-python; else uv sync --project backend --frozen --extra dev $research_extra --no-install-project --no-managed-python; fi \
    && useradd --uid 10001 --create-home appuser
COPY backend/ backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    research_extra=""; if [ "$INSTALL_EVALUATION" = true ]; then research_extra="--extra evaluation"; fi; \
    if [ "$INSTALL_ML" = true ]; then uv sync --project backend --frozen --extra dev --extra ml $research_extra --no-managed-python; else uv sync --project backend --frozen --extra dev $research_extra --no-managed-python; fi
COPY scripts/ scripts/
COPY evaluation/annotation/ evaluation/annotation/
COPY evaluation/agent/ evaluation/agent/
COPY .env.example .env.example
COPY ruff.toml ruff.toml
USER appuser
EXPOSE 8000
CMD ["sh", "scripts/runtime/start_backend.sh"]
