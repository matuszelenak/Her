FROM python:3.12-slim-bookworm

RUN apt update && apt install -y gcc libpq-dev ncat

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
