---
name: minhas-tasks
description: Lista as tasks do Jira atribuídas a quem está usando, na sprint aberta, com status e bloqueios, e sugere qual pegar a seguir. Use quando a pessoa perguntar "o que eu faço agora", "minhas tasks", "o que está comigo".
---

# /minhas-tasks

Só leitura. Não move nem comenta nada.

## Passos

1. Pelo MCP Atlassian (cloudId `66a6b7ba-aa8e-4bb8-8231-c34965b450e1`), busque:
   ```
   project = SCRUM AND assignee = currentUser() AND sprint in openSprints() ORDER BY status DESC, rank ASC
   ```
   Se vier vazio, tente sem o filtro de sprint e com `statusCategory != Done`. Avise que não há
   nada na sprint aberta.
2. Para cada issue, traga:
   - chave;
   - resumo;
   - status;
   - épico/história pai;
   - links do tipo "is blocked by" (bloqueada por).
3. Para cada bloqueio, diga se a issue bloqueadora já está `Concluído`.
4. Mostre uma tabela curta, nesta ordem:
   - `Em análise`: aguardando revisão, cobre o revisor;
   - `Em andamento`: termine antes de pegar outra;
   - `A fazer` sem bloqueio aberto;
   - `A fazer` bloqueada: diga por quem.
5. Termine com **uma** sugestão: "Próxima: SCRUM-NN, porque…". Para escolher:
   - termine o que está em andamento antes de pegar nova;
   - entre as livres, prefira a de maior prioridade no board (rank).
   - Para começar, rode `/comecar-task SCRUM-NN`.

## Não faça

- Não sugira pegar task atribuída a outra pessoa.
- Se a pessoa quiser trocar, ela fala com o PO.
