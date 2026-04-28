FROM node:24-bookworm-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM python:3.14-slim-bookworm

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

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
