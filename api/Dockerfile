FROM python:3.14-slim AS deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/
WORKDIR /srv/app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

FROM deps AS base
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY migrations ./migrations
COPY alembic.ini ./
COPY --chmod=755 scripts/entrypoint.sh ./scripts/
ENV PATH="/srv/app/.venv/bin:$PATH"

FROM deps AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen
COPY migrations ./migrations
COPY alembic.ini ./
COPY tests ./tests
COPY scripts ./scripts
ENV PATH="/srv/app/.venv/bin:$PATH"

FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /srv/app
RUN useradd --create-home appuser
COPY --from=base /srv/app ./
ENV PATH="/srv/app/.venv/bin:$PATH"
USER appuser
ENTRYPOINT ["./scripts/entrypoint.sh"]
