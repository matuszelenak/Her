FROM python:3.12-alpine3.20

RUN apk update

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--timeout-graceful-shutdown", "0"]
