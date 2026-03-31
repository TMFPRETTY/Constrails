FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY policies ./policies
COPY .env.example ./.env.example

RUN pip install --upgrade pip setuptools wheel && \
    pip install .

EXPOSE 8000

CMD ["constrail", "serve", "--host", "0.0.0.0", "--port", "8000"]
