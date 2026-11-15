# Imagem do worker de ingestão. Roda um ciclo e sai (o cron chama de novo).
#   docker compose run --rm worker
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY worker/requirements.txt worker/requirements.txt
RUN pip install --no-cache-dir -r worker/requirements.txt

# O worker lê as migrações para criar o banco de teste do `avaliar`; o resto vem de worker/.
COPY shared/migrations shared/migrations
COPY worker worker

CMD ["python", "-m", "worker", "--uma-vez"]
