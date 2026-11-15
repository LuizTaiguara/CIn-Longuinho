# Achados e Perdidos — CIn-UFPE

Catálogo pesquisável para a lista `achados-perdidos@cin.ufpe.br`. Projeto da disciplina
IESI (CIN0139), UFPE 2026.2.

```
worker/   Python — ETL agendado: lê e-mail, classifica, extrai, grava
site/     JavaScript — catálogo web
shared/   contrato da API e schema (área protegida)
docs/     arquitetura, ADRs, backlog, diagramas, equipe
.agents/  skills e configuração MCP do time para o AGY
```

**Comece por:** `docs/ARQUITETURA.md` (o porquê) e `docs/BACKLOG.md` (o quê).

---

## O que é cada pasta

* **`worker/`**: Script Python de ingestão de mensagens. Processo agendado (*batch job*) que lê e-mails, classifica, extrai entidades via NER (GLiNER) e grava no banco de dados (`docs/ARQUITETURA.md` §1.2, §2.1).
* **`site/`**: Aplicação web em JavaScript que permanece de pé: catálogo web (`docs/ARQUITETURA.md` §2.1).
* **`shared/`**: Modelos compartilhados e especificação da API REST (`openapi.yaml` — *disponível após o PR #8*). É uma área protegida sob governança compartilhada entre os subgrupos (`shared/AGENTS.md`, `docs/ADR.md` ADR-008).
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

## Como rodar o ambiente

### O que funciona hoje no repositório

* Clonar o repositório e preparar o arquivo `.env`.
* Inspecionar o corpus curado de testes e casos reais em `worker/corpus/casos/`.
* **Subir o banco PostgreSQL com as migrações aplicadas** (SCRUM-70):
  ```bash
  docker compose up -d banco
  ```
  As migrações de `shared/migrations/` rodam na primeira subida do volume. Para recomeçar do
  zero: `docker compose down -v`. Para conferir as regras do banco (append-only, situação que
  só avança): `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f shared/testes/test_regras_banco.sql`.
* **Rodar os testes do worker** (leitor de `.eml` contra o corpus):
  ```bash
  python -m unittest discover worker/testes
  ```
* **Rodar o site com o mock local:** ver `site/AGENTS.md` (`npm install`, `npm run dev`).

### Próximos passos e comandos previstos

* **Executar o worker de ingestão:** `(disponível quando a task correspondente for concluída)`
* **Executar a API:** ver "Rodar a API" abaixo.

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
3. Abra o PR com `/abrir-pr`. O revisor segue `docs/EQUIPE.md`, e ninguém faz merge do próprio PR.
4. O PO aceita contra o critério e move para Concluído.
