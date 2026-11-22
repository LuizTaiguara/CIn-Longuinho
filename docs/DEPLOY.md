# Deploy em uma VPS

Como pôr o catálogo no ar num servidor próprio, com HTTPS, e como mantê-lo. Nenhuma credencial fica
neste arquivo nem no repositório: tudo o que é segredo vive no `.env` da VPS e em `worker/.segredos/`.

**Estado em 22/11/2026:** os arquivos estão prontos e foram validados em máquina local
(`docker compose config`, rotas do Caddy, backup e restauração). **O deploy em si ainda não foi feito.**
Os passos 4 a 7 dependem de coisas que só quem tem as contas pode fazer.

## O que sobe

| Peça | O que é | Exposta? |
|---|---|---|
| `caddy` | Porta de entrada. Cuida do HTTPS e reparte: `/api/*` vai para a API, o resto para o site | **Sim**, portas 80 e 443 |
| `site` | nginx com o build do site | Não |
| `api` | FastAPI | Não |
| `banco` | PostgreSQL 16 | Não |
| `worker` | Roda um ciclo e sai. Quem chama é o cron, a cada 5 minutos | Não |

Volumes nomeados: `banco-dados` (o banco), `api-dados` (as fotos), `worker-modelos` (o modelo do GLiNER,
~1,2 GB), `caddy-dados` e `caddy-config` (certificados).

## Antes de começar

- Uma VPS com Linux, pelo menos **2 GB de RAM** e **10 GB de disco livre**. O worker carrega o modelo
  de extração na memória a cada ciclo; com 1 GB ele não roda. *(Estimativa feita a partir do uso local;
  confira na VPS com `docker stats` durante um ciclo.)*
- As portas **80 e 443 livres** e abertas no firewall. Se já houver outro servidor web nelas, pare aqui:
  é preciso decidir como os dois convivem.
- Um domínio (ou subdomínio) com o **DNS apontando para o IP da VPS**. Sem isso o Caddy não consegue o
  certificado.
- Docker com o plugin Compose **2.24 ou mais novo** (`docker compose version`).

## 1. Instalar o Docker

Siga a instalação oficial para a sua distribuição: <https://docs.docker.com/engine/install/>. Depois:

```bash
sudo usermod -aG docker "$USER"     # e entre de novo na sessão
docker compose version              # precisa ser 2.24 ou mais novo
```

## 2. Clonar

```bash
sudo mkdir -p /opt/longuinho && sudo chown "$USER" /opt/longuinho
git clone https://github.com/LuizTaiguara/CIn-Longuinho.git /opt/longuinho
cd /opt/longuinho
```

Os exemplos abaixo usam `/opt/longuinho`. Se usar outra pasta, troque também nas linhas do cron.

## 3. Escrever o `.env` de produção

```bash
cp .env.example .env
chmod 600 .env
```

Edite o `.env`. O que **precisa** mudar em relação ao exemplo:

| Variável | Valor em produção |
|---|---|
| `COMPOSE_FILE` | `docker-compose.yml:docker-compose.prod.yml` (descomente a linha) |
| `DOMINIO` | o domínio, sem `https://` |
| `POSTGRES_PASSWORD` | uma senha longa e aleatória, só com letras e números (ela entra numa URL) |
| `SESSAO_SEGREDO` | um segredo longo e aleatório: `openssl rand -hex 32` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | os do client OAuth "Aplicativo da Web" (passo 4) |
| `LOGIN_SIMULADO` | **vazio** |
| `VITE_EMAIL_REMOCAO` | o endereço `+remocao` da conta do projeto (aparece no rodapé) |
| `EMAIL_MODO_ENVIO` | `smtp` |
| `EMAIL_REMETENTE`, `SMTP_USUARIO` | o endereço da conta Gmail do projeto |
| `SMTP_SENHA` | uma **senha de app** do Gmail do projeto (passo 5) |
| `WORKER_FONTE_MENSAGENS` | `gmail` |
| `WORKER_AVISO_A_PARTIR_DE` | a data de hoje, `AAAA-MM-DD` (ver o aviso abaixo) |

`SITE_URL`, `API_URL`, `GOOGLE_REDIRECT_URI` e `DATABASE_URL` não precisam ser mexidos: em produção o
`docker-compose.prod.yml` os monta a partir de `DOMINIO` e da senha do banco.

> **`WORKER_AVISO_A_PARTIR_DE` não é detalhe.** A primeira leitura do Gmail traz tudo o que está na caixa.
> Sem essa data, o aviso ao autor não sai para ninguém. Com uma data antiga, sai para anúncios velhos.
> Ponha a data em que o worker começa a ler a lista.

> **A senha do banco só vale na primeira subida.** O Postgres grava a senha quando cria o volume. Se
> trocar `POSTGRES_PASSWORD` depois, troque também dentro do banco (`ALTER USER`), ou a API não conecta.

## 4. Google OAuth em produção (login com a conta do CIn)

No Google Cloud Console, no projeto da equipe:

1. *APIs e serviços → Tela de consentimento OAuth*: tipo **Externo**, só os escopos `openid`, `email` e
   `profile`.
2. *Credenciais → Criar credenciais → ID do cliente OAuth*, tipo **Aplicativo da Web**.
3. Em *URIs de redirecionamento autorizados*, cadastre exatamente:
   `https://<dominio>/api/auth/google/callback`
4. Copie o ID e a chave secreta para `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env`.

`SITE_URL` e `API_URL` apontam para `https://<dominio>`; o compose de produção já faz isso. Só entram
contas `@cin.ufpe.br` com e-mail verificado: quem confere é a API.

**Ainda não testado:** o login com uma conta `@cin.ufpe.br` real por um app externo (risco R8 do
backlog). Se o CIn bloquear, a US-15 fica parada e a questão volta ao PO.

## 5. A conta Gmail do projeto

Duas coisas diferentes usam a conta do projeto. Quem é o dono dela e como passá-la adiante está em
`docs/PASSAGEM.md`.

**Ler a lista (worker).** Usa a API do Gmail, só leitura.

1. No Google Cloud Console, ative a *Gmail API* e crie outro client OAuth, do tipo **App para computador**.
   Baixe o JSON.
2. Numa máquina **com navegador** (não na VPS), com o repositório clonado:
   ```bash
   mkdir -p worker/.segredos
   # ponha o JSON baixado em worker/.segredos/credenciais.json
   GMAIL_PROJECT_CREDENTIALS_FILE=worker/.segredos/credenciais.json python -m worker.autorizar_gmail
   ```
   O navegador abre; entre com a **conta do projeto** e aceite o acesso de leitura. Sai o arquivo
   `worker/.segredos/token.json`.
3. Copie os dois arquivos para a VPS, em `/opt/longuinho/worker/.segredos/`, por um canal seguro
   (`scp`). Nunca por e-mail nem por chat.
   ```bash
   chmod 700 worker/.segredos && chmod 600 worker/.segredos/*
   ```

> **Ponto a conferir, não testado aqui:** pela documentação do Google, um app OAuth externo com a tela de
> consentimento em modo **"Teste"** recebe um token que **expira em 7 dias** quando pede escopo do Gmail.
> Se isso acontecer, o worker passa a sair com "credencial da fonte expirada" e o catálogo para de receber
> anúncios. A saída é publicar o app ("Em produção") na tela de consentimento. Confira na primeira semana.

**Enviar e-mail (API e worker).** O contato com quem anunciou e o aviso ao autor saem por SMTP.

1. Na conta do projeto, ative a verificação em duas etapas e crie uma **senha de app**.
2. Ponha essa senha em `SMTP_SENHA`. `SMTP_HOST=smtp.gmail.com` e `SMTP_PORT=587` já estão no exemplo.

O sistema nunca posta na lista.

## 6. Subir

```bash
cd /opt/longuinho
docker compose config --quiet && echo "configuração ok"
docker compose up -d --build
docker compose ps
```

Confira:

```bash
curl -sI https://<dominio>/ | head -1                  # HTTP/2 200
curl -s  https://<dominio>/api/locais | head -c 200    # a lista de locais, em JSON
```

O primeiro acesso pode levar um minuto: é o Caddy pedindo o certificado. Se não vier, veja
`docker compose logs caddy` (quase sempre é DNS ou porta fechada).

As migrações de `shared/migrations/` rodam sozinhas **só na primeira subida do banco**.

## 7. Ligar o worker e o backup no cron

Rode o worker uma vez à mão. O primeiro ciclo baixa o modelo (~1,2 GB) e demora alguns minutos:

```bash
docker compose run --rm worker
```

A última linha deve ser `ciclo concluído: lidas=… novas=…`. Depois, `crontab -e`:

```cron
# Longuinho: worker a cada 5 minutos
*/5 * * * * cd /opt/longuinho && docker compose run --rm -T worker >> /var/log/longuinho-worker.log 2>&1
# Longuinho: backup diário às 3h15, guardando 14 dias
15 3 * * * /opt/longuinho/deploy/backup.sh >> /var/log/longuinho-backup.log 2>&1
```

Crie os arquivos de log e a pasta de backup uma vez:

```bash
sudo touch /var/log/longuinho-worker.log /var/log/longuinho-backup.log
sudo mkdir -p /var/backups/longuinho
sudo chown "$USER" /var/log/longuinho-*.log /var/backups/longuinho
```

Se um ciclo demorar mais de 5 minutos, o seguinte percebe, registra "outra execução do worker está em
andamento" e sai. Não há risco de dois ciclos processarem a mesma mensagem.

## Operação

### Ver o que está acontecendo

```bash
docker compose ps
docker compose logs --tail 100 api
docker compose logs --tail 100 caddy
tail -n 50 /var/log/longuinho-worker.log
```

Códigos de saída do worker: `0` ciclo ok; `1` a fonte falhou (token do Gmail expirado ou Gmail fora do ar);
`2` banco indisponível.

**Como perceber que parou de receber:** a lista continua recebendo e-mails e nenhum anúncio novo aparece
no catálogo. O worker não tem como distinguir "ninguém anunciou" de "o encaminhamento foi desfeito".
Olhe o log do worker: `novas=0` por dias seguidos, com a lista ativa, é o sinal. O que fazer está em
`docs/PASSAGEM.md`.

### Atualizar

```bash
cd /opt/longuinho
git pull
ls shared/migrations/                 # apareceu arquivo novo? aplique antes de subir (abaixo)
docker compose up -d --build
```

Migração nova não roda sozinha num banco que já existe. Aplique à mão, uma vez, na ordem dos números:

```bash
docker compose exec -T banco sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < shared/migrations/NNN_nome.sql
```

Mudou `VITE_EMAIL_REMOCAO`? O site precisa ser reconstruído: `docker compose up -d --build site`.

### Backup

`deploy/backup.sh` grava, por dia, `banco-AAAA-MM-DD.dump` e `fotos-AAAA-MM-DD.tar` em
`/var/backups/longuinho` e apaga o que tem mais de 14 dias. Para mudar a pasta ou o prazo, use
`BACKUP_DIR` e `BACKUP_DIAS`.

**O backup tem dado pessoal** (os e-mails de quem anunciou e as mensagens originais). Ele fica só na VPS.
Se for copiar para outro lugar, só para um lugar privado.

Um backup no mesmo disco não protege contra a perda da VPS. Copiar para fora é decisão de quem opera.

### Restaurar

Para conferir um backup sem tocar no banco de verdade:

```bash
docker compose exec -T banco sh -c 'createdb -U "$POSTGRES_USER" restauracao_teste \
  && pg_restore -U "$POSTGRES_USER" -d restauracao_teste' < /var/backups/longuinho/banco-AAAA-MM-DD.dump
docker compose exec -T banco sh -c 'psql -U "$POSTGRES_USER" -d restauracao_teste -c "select count(*) from item"'
docker compose exec -T banco sh -c 'dropdb -U "$POSTGRES_USER" restauracao_teste'
```

Para restaurar de verdade, numa VPS nova ou depois de perder o volume:

```bash
docker compose up -d banco            # volume novo: o banco sobe vazio, com as migrações aplicadas
docker compose stop api
docker compose exec -T banco sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  < /var/backups/longuinho/banco-AAAA-MM-DD.dump
docker compose up -d
docker compose exec -T api tar -C /app/dados -xf - < /var/backups/longuinho/fotos-AAAA-MM-DD.tar
```

As tabelas `mensagem_bruta` e `evento` não aceitam `DELETE` (invariante 4). Por isso a restauração é feita
num banco recém-criado, e não por cima de um banco em uso.

### Parar tudo

```bash
docker compose down        # para os contêineres; os dados ficam nos volumes
```

`docker compose down -v` **apaga o banco, as fotos e os certificados**. Não use em produção.

## O que este deploy não faz

- Não monitora nem avisa ninguém quando algo cai. Quem percebe é quem olha.
- Não copia o backup para fora da VPS.
- Não atualiza sozinho.

Isso é coerente com a restrição R6: o sistema precisa ficar de pé sem ninguém cuidando. Se o worker parar,
o catálogo continua no ar com o que já tem.
