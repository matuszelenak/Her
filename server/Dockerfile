FROM python:3.12-slim-bookworm

RUN apt update && apt install -y gcc libpq-dev ncat

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY server.py server.py
COPY utils utils
COPY tasks tasks
COPY db db
COPY providers providers
COPY config.json config.json
COPY alembic.ini alembic.ini
COPY endpoints endpoints

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
