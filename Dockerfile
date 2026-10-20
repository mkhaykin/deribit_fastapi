FROM python:3.12-slim

LABEL maintainer="mkhaikin@yandex.ru"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --create-home appuser

COPY ./src /app
COPY ./migrations /app/migrations

RUN chown -R appuser:appgroup /app

USER appuser
