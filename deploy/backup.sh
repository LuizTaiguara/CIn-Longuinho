#!/bin/sh
# Backup diário do banco e das fotos (SCRUM-108). Rode pelo cron da VPS:
#
#   15 3 * * * /opt/longuinho/deploy/backup.sh >> /var/log/longuinho-backup.log 2>&1
#
# Guarda um arquivo por dia em BACKUP_DIR (padrão /var/backups/longuinho) e apaga os que têm mais
# de BACKUP_DIAS dias (padrão 14). Não lê o .env: usuário e nome do banco vêm de dentro do contêiner.
#
# ATENÇÃO: o backup contém os e-mails de quem anunciou e as mensagens originais. Ele fica só na
# VPS, com permissão restrita. Nunca o suba para o repositório nem para pasta compartilhada.
set -eu
umask 077

DESTINO="${BACKUP_DIR:-/var/backups/longuinho}"
DIAS="${BACKUP_DIAS:-14}"
HOJE="$(date +%F)"

cd "$(dirname "$0")/.."
mkdir -p "$DESTINO"

# Grava num arquivo ".parcial" e só renomeia se o comando terminou bem: um backup pela metade
# nunca fica com nome de backup bom.
docker compose exec -T banco sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$DESTINO/banco-$HOJE.dump.parcial"
mv "$DESTINO/banco-$HOJE.dump.parcial" "$DESTINO/banco-$HOJE.dump"

docker compose exec -T api tar -C /app/dados -cf - fotos > "$DESTINO/fotos-$HOJE.tar.parcial"
mv "$DESTINO/fotos-$HOJE.tar.parcial" "$DESTINO/fotos-$HOJE.tar"

find "$DESTINO" -maxdepth 1 -type f \( -name 'banco-*.dump' -o -name 'fotos-*.tar' \) -mtime +"$DIAS" -delete

echo "$(date '+%F %T') backup ok: $(ls -1 "$DESTINO" | wc -l) arquivos em $DESTINO"
