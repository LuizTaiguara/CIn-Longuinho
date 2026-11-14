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

### Próximos passos e comandos previstos

* **Subir o banco PostgreSQL via Docker Compose:** `(disponível após a SCRUM-70)`
* **Executar as migrações do schema no banco de dados:** `(disponível após a SCRUM-69 e SCRUM-70)`
* **Executar o worker de ingestão:** `(disponível quando a task correspondente for concluída)`
* **Executar o site / catálogo:** `(disponível quando a task correspondente for concluída)`

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
