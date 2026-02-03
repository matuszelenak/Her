#!/bin/bash
set -e

which python
uv run alembic upgrade head || { echo 'Migrations failed! Exiting.'; exit 1; }
exec uv run uvicorn server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 0 "$@"
