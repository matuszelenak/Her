FROM python:3.12-slim-bookworm

RUN apt update && apt install -y gcc libpq-dev

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--timeout-graceful-shutdown", "0"]
