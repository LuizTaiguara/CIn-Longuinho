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

## Uso de IA no time

O contexto de IA é comum a todos e vive no repositório:

- `AGENTS.md` (raiz e por pasta): regras que qualquer agente lê ao abrir o projeto.
  `CLAUDE.md` só aponta para ele.
- `.agents/skills/`: `/minhas-tasks`, `/comecar-task`, `/abrir-pr`, `/revisar-pr`.
- `.agents/mcp_config.json`: conexão com o Jira (cada pessoa autentica com a própria conta).

A IA errou algo que o contexto deveria ter evitado? Corrija o `AGENTS.md` e abra um PR.

## Fluxo

1. Pegue a task no Jira: `/minhas-tasks` e depois `/comecar-task SCRUM-NN`.
2. Trabalhe numa branch `SCRUM-NN-descricao`. Nunca direto na `main`.
3. Abra o PR com `/abrir-pr`. O revisor segue `docs/EQUIPE.md`, e ninguém faz merge do próprio PR.
4. O PO aceita contra o critério e move para Concluído.
