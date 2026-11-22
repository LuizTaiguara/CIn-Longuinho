# Imagem da API. Construa a partir da raiz do repositório:
#   docker compose build api      (ou: docker build -f api/Dockerfile .)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/ api/

# Fotos enviadas (US-06) e e-mails gravados em arquivo. No compose, /app/dados é o volume `api-dados`.
RUN mkdir -p /app/dados/fotos /app/dados/emails-enviados && useradd --system --uid 1000 api && chown -R api /app/dados
USER api

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
