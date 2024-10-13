FROM python:3.12-alpine3.20

RUN apk update

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY server.py server.py
COPY utils utils
COPY tasks tasks
COPY config.json config.json

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
