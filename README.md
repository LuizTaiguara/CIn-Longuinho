# Achados e Perdidos — CIn-UFPE

Catálogo pesquisável para a lista `achados-perdidos@cin.ufpe.br`. Projeto da disciplina
IESI (CIN0139), UFPE 2026.2.

```
worker/   Python — ETL agendado: lê e-mail, classifica, extrai, grava
api/      Python (FastAPI) — a única porta do site para os dados
site/     JavaScript — catálogo web
shared/   contrato da API e schema (área protegida)
docs/     arquitetura, ADRs, backlog, diagramas, equipe
.agents/  skills e configuração MCP do time para o AGY
```

**Comece por:** `docs/ARQUITETURA.md` (o porquê) e `docs/BACKLOG.md` (o quê).

---

## Como rodar tudo

Só precisa de Docker. Não precisa de credencial do Google nem de internet depois do primeiro ciclo.

```bash
cp .env.example .env                    # uma vez
docker compose up -d banco api site     # banco com as migrações, API (porta 8000) e site (porta 8080)
docker compose run --rm worker          # um ciclo do worker sobre o corpus de worker/corpus/casos
```

Abra <http://localhost:8080>: o catálogo aparece com os itens do corpus.

- O primeiro ciclo do worker baixa o modelo do GLiNER (~1,2 GB) para um volume; os seguintes levam segundos.
- Para entrar sem Google, ponha `LOGIN_SIMULADO=fic.ana.lemos@cin.ufpe.br` no `.env` (a autora do caso 1
  do corpus) e rode `docker compose up -d api` de novo.
- Para ver os e-mails que o sistema mandaria, ponha `EMAIL_MODO_ENVIO=arquivo` e olhe
  `docker compose exec api ls /app/dados/emails-enviados`.
- Recomeçar do zero: `docker compose down -v` (apaga o banco, as fotos e o cache do modelo).

Os testes também rodam em contêiner, sem instalar Python nem Node na máquina:

```bash
docker compose run --rm -v "$PWD/worker:/app/worker" worker python -m pytest worker/testes -q
docker compose run --rm -v "$PWD/api:/app/api:ro" -v "$PWD/shared:/app/shared:ro" api \
  python -m pytest api/testes -q -p no:cacheprovider
docker compose run --rm worker python -m worker.avaliar    # corpus × gabarito do PO
(cd site && npm ci && npm test)                            # o site precisa de Node 20 ou mais novo
```

---

## O que é cada pasta

* **`worker/`**: Script Python de ingestão de mensagens. Processo agendado (*batch job*) que lê e-mails, classifica, extrai entidades via NER (GLiNER) e grava no banco de dados (`docs/ARQUITETURA.md` §1.2, §2.1).
* **`site/`**: Aplicação web em JavaScript que permanece de pé: catálogo web (`docs/ARQUITETURA.md` §2.1).
* **`shared/`**: Schema do banco (`migrations/`) e especificação da API REST (`openapi.yaml`). É uma área protegida sob governança compartilhada entre os subgrupos (`shared/AGENTS.md`, `docs/ADR.md` ADR-008).
* **`docs/`**: Documentação técnica completa do projeto: arquitetura, registros de decisões arquiteturais (ADRs), backlog com critérios de aceitação, diagramas e divisão da equipe.
* **`.agents/`**: Definições de *skills* e configurações de ferramentas de IA (MCP) para automação e padronização do fluxo do time.

---

## Por que worker e site são processos separados

A separação estrita entre o `worker/` e o `site/` decorre de decisões centrais de arquitetura:

1. **Repositório compartilhado (*shared-data*):** O banco de dados PostgreSQL é o único ponto de integração entre os dois componentes. Worker e site **não se conhecem e não se comunicam diretamente** (`docs/ARQUITETURA.md` §1.2, §3.2; `docs/ADR.md` ADR-001).
2. **Tolerância a falhas parciais:** **Falha no worker não derruba o site.** Se o pipeline de ingestão falhar ou for interrompido, o catálogo continua de pé respondendo normalmente a consultas e buscas públicas — apenas deixa de receber itens novos momentaneamente (`docs/ARQUITETURA.md` §1.2, §3.2, §3.3).
3. **Ciclos de vida e naturezas distintas:** O worker é um processo em lote agendado que acorda, executa o pipeline e termina; o site é um serviço web contínuo que precisa responder requisições imediatamente (`docs/ARQUITETURA.md` §2.1).
4. **Isolamento de recursos e dependências:** O worker carrega o modelo de extração NER (GLiNER) no ecossistema Python; o processo que serve as páginas não tem motivo para carregar esse modelo (`docs/ARQUITETURA.md` §1.2, §2.4).
5. **Desenvolvimento e implantação independentes:** Cada processo pode ser desenvolvido, testado e implantado de maneira autônoma (`docs/ARQUITETURA.md` §1.2; `docs/ADR.md` ADR-001).

---

## Como clonar e configurar o ambiente

### 1. Clonar o repositório

```bash
git clone https://github.com/LuizTaiguara/CIn-Longuinho.git
cd CIn-Longuinho
```

### 2. Configurar variáveis de ambiente

O projeto adota configuração estritamente por variáveis de ambiente, sem nenhuma credencial em código (`docs/ARQUITETURA.md` §2.4; Invariante 9). Copie o arquivo de exemplo para `.env`:

* **Bash:**
  ```bash
  cp .env.example .env
  ```
* **PowerShell:**
  ```powershell
  Copy-Item .env.example .env
  ```

Edite o arquivo `.env` para ajustar os parâmetros locais. O arquivo `.env` real está protegido no `.gitignore` e nunca deve ser commitado.

---

## Como rodar sem credencial do Google (F-03)

O sistema foi desenhado para desenvolvimento, teste e demonstração **sem dependência de credenciais externas e sem necessidade de conexão com o Google** (`docs/ARQUITETURA.md` §2.3; `docs/ADR.md` ADR-003, ADR-011):

* **Worker offline:** A fonte de leitura opera atrás de uma abstração com implementações trocáveis. Ao configurar `WORKER_FONTE_MENSAGENS=arquivos_locais`, o pipeline lê diretamente os arquivos `.eml` do corpus de testes localizado em `worker/corpus/casos/`. O envio deve ser configurado como `WORKER_MODO_ENVIO=nao_enviar` (`worker/AGENTS.md`, `docs/ADR.md` ADR-003).
* **Catálogo anônimo:** A consulta e a busca no catálogo web são públicas e não exigem autenticação (`docs/BACKLOG.md` US-04). A dependência do Google OAuth restringe-se exclusivamente à gestão de anúncios pelo próprio autor (`docs/ADR.md` ADR-010; `docs/BACKLOG.md` US-15).

---

## Como rodar cada parte

O caminho curto está em "Como rodar tudo", no começo deste arquivo. Aqui ficam os detalhes de cada parte,
para quem desenvolve fora do contêiner.

* **Banco PostgreSQL com as migrações aplicadas** (SCRUM-70):
  ```bash
  docker compose up -d banco
  ```
  As migrações de `shared/migrations/` rodam na primeira subida do volume. Para recomeçar do
  zero: `docker compose down -v`. Para conferir as regras do banco (append-only, situação que
  só avança): `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f shared/testes/test_regras_banco.sql`.
* **Worker de ingestão** (detalhes em `worker/AGENTS.md`, seção "Comandos"):
  ```bash
  python -m venv .venv && . .venv/bin/activate
  pip install -r worker/requirements.txt
  docker compose up -d banco
  python -m pytest worker/testes            # testes (usam o banco <nome>_teste_worker)
  python -m worker --fonte arquivos --dir worker/corpus/casos --uma-vez   # um ciclo sobre o corpus
  docker compose run --rm worker            # o mesmo ciclo, em contêiner
  ```
  Em produção, o worker roda por cron e morre a cada ciclo:
  `*/5 * * * * cd /caminho && docker compose run --rm worker`

  Para ler a conta Gmail do projeto: ponha o JSON do client OAuth em `worker/.segredos/credenciais.json`,
  rode `python -m worker.autorizar_gmail` uma vez (abre o navegador) e use `WORKER_FONTE_MENSAGENS=gmail`.
  Para o aviso ao autor sair, defina `WORKER_AVISO_A_PARTIR_DE` e `EMAIL_MODO_ENVIO=smtp`.
* **Rodar o site:** ver a subseção abaixo e `site/AGENTS.md`.

### Rodar o site

```bash
cd site
npm ci
npm run dev                                   # com o mock local, sem backend: http://localhost:5173
API_URL=http://localhost:8000 npm run dev     # contra a API de verdade, que precisa estar de pé
npm test                                      # testes (sem internet e sem credencial)
```

Para subir a versão de produção (build servido por nginx, que repassa `/api/` para a API), da raiz:

```bash
docker compose up -d --build api site         # site em http://localhost:8080, API em :8000
```

O `.env.example` já traz `SITE_URL=http://localhost:8080`, para o login voltar ao site do compose.
Se o site estiver rodando com `npm run dev`, troque para `http://localhost:5173`.

Sem `API_URL`, o site usa um mock local das 14 rotas do contrato, com login simulado (o botão
"Entrar com a conta do CIn" entra direto, sem Google). Os estados de erro e vazio se veem com
`MOCK_VAZIO=1`, `MOCK_FALHA=1`, `MOCK_CONTATO_FALHA=1` e `MOCK_LOGIN_FORA=1` (detalhes em
`site/AGENTS.md`).

### Rodar a API

A API (FastAPI, Python 3.12) é a única porta do site para os dados. Contrato: `shared/openapi.yaml`,
todas as rotas sob `/api`. Detalhes e regras em `api/AGENTS.md`.

```bash
# uma vez: ambiente Python da API
python3.12 -m venv api/.venv
api/.venv/bin/pip install -r api/requirements.txt

# com o banco no ar (docker compose up -d banco), da raiz do repositório:
api/.venv/bin/uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/api/itens

# ou tudo em contêiner (banco + API):
docker compose up -d api

# testes (usam o Postgres do compose, num banco à parte chamado longuinho_teste_api):
api/.venv/bin/python -m pytest api/testes
```

**Entrar sem Google (desenvolvimento).** Ponha no `.env` um endereço fictício do CIn, por exemplo
`LOGIN_SIMULADO=fic.teste@cin.ufpe.br`. Aí `GET /api/auth/google` cria a sessão direto, com o nome
"Pessoa de Teste", e volta ao site. A API **recusa subir** com `LOGIN_SIMULADO` preenchido se
`SITE_URL` for `https://`: em produção ele fica vazio.

**Login Google de verdade.** Crie o client OAuth uma vez, no Google Cloud Console da conta do projeto:

1. *APIs e serviços → Tela de consentimento OAuth*: tipo **Externo**, só os escopos de identidade
   (`openid`, `email`, `profile`). Nenhum escopo sensível.
2. *Credenciais → Criar credenciais → ID do cliente OAuth*: tipo **Aplicativo da Web**.
3. Em *URIs de redirecionamento autorizados*, cadastre `API_URL/api/auth/google/callback`
   (em desenvolvimento, `http://localhost:8000/api/auth/google/callback`; é o `GOOGLE_REDIRECT_URI`).
4. Copie o ID e a chave secreta para `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env` (nunca no código).

Só contas `@cin.ufpe.br` com e-mail verificado entram: a conferência é feita pela API, e o `hd`
mandado ao Google é só dica de tela.

**E-mail de contato (US-05).** O botão de contato manda a mensagem pela conta do projeto, sem mostrar
o endereço de quem anunciou. `EMAIL_MODO_ENVIO` escolhe o que acontece:

- `nao_enviar` (padrão): nada sai; a API só registra no log que descartou.
- `arquivo`: cada mensagem vira um `.eml` em `EMAIL_ARQUIVO_DIR`, para conferir o que sairia.
- `smtp`: envia pelo Gmail do projeto (`SMTP_HOST=smtp.gmail.com`, porta 587, senha de app em
  `SMTP_SENHA`). **Só em produção.** A API não sobe em `smtp` sem `EMAIL_REMETENTE` e `SMTP_*` reais.

O sistema nunca posta na lista.

---

## Uso de IA no time

O contexto de IA é comum a todos e vive no repositório:

- `AGENTS.md` (raiz e por pasta): regras que qualquer agente lê ao abrir o projeto.
  `CLAUDE.md` só aponta para ele.
- `.agents/skills/`: `/minhas-tasks`, `/comecar-task`, `/abrir-pr`, `/revisar-pr`.
- `.agents/mcp_config.json`: conexão com o Jira (cada pessoa autentica com a própria conta).

A IA errou algo que o contexto deveria ter evitado? Corrija o `AGENTS.md` e abra um PR.

---

## Fluxo

1. Pegue a task no Jira: `/minhas-tasks` e depois `/comecar-task SCRUM-NN`.
2. Trabalhe numa branch `SCRUM-NN-descricao`. Nunca direto na `main`.
3. Abra o PR com `/abrir-pr`. O revisor segue `docs/EQUIPE.md`, e ninguém faz merge do próprio PR
   (a exceção do PO está no `AGENTS.md`).
4. O PO aceita contra o critério e move para Concluído.
