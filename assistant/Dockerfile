FROM python:3.13.11-slim-trixie@sha256:51e1a0a317fdb6e170dc791bbeae63fac5272c82f43958ef74a34e170c6f8b18
COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /bin/

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt update && apt install -y gcc libpq-dev ncat

WORKDIR /app

COPY pyproject.toml pyproject.toml
RUN uv sync

COPY src src
COPY server.py server.py

ENTRYPOINT ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--timeout-graceful-shutdown", "0"]
