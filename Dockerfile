FROM node:24-bookworm-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM python:3.14-slim-bookworm

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH="/app/data/app.db"
ENV PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

RUN pip install --no-cache-dir uv==0.11.8
RUN mkdir -p /app/data

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev

COPY backend ./
COPY --from=frontend-build /app/frontend/out ./static

# Run as a non-root user. UID/GID can be overridden at build time so the
# bind-mounted /app/data is writable from the host (typically pass `id -u`
# and `id -g` from the start scripts).
RUN groupadd --gid ${APP_GID} app \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --no-create-home app \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
