FROM python:3.13.11-slim-trixie@sha256:51e1a0a317fdb6e170dc791bbeae63fac5272c82f43958ef74a34e170c6f8b18
COPY --from=ghcr.io/astral-sh/uv:latest  /uv /uvx /bin/

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt update && apt install -y gcc libpq-dev ncat curl

WORKDIR /app

COPY pyproject.toml pyproject.toml
RUN uv sync

COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

COPY alembic.ini alembic.ini
COPY src src
COPY server.py server.py
COPY config.template.json config.template.json

HEALTHCHECK --interval=10s --timeout=10s --retries=1 --start-period=30s CMD curl --fail http://localhost:8000/health || exit 1
ENTRYPOINT ["./entrypoint.sh"]
