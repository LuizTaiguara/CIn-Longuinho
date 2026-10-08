---
name: comecar-task
description: Começa uma task do Jira (SCRUM-NN). Lê a task e os critérios de aceitação, cria a branch, move para "Em andamento" e propõe um plano antes de escrever código. Use quando a pessoa disser "vou começar a SCRUM-NN", "pegar task", "começar task".
---

# /comecar-task SCRUM-NN

Objetivo: sair daqui com **contexto certo e um plano aprovado**, não com código.

## Passos

1. **Chave.** Se a pessoa não passou `SCRUM-NN`, rode o procedimento de `/minhas-tasks` e pergunte qual é.
2. **Ler a task** pelo MCP Atlassian (cloudId `66a6b7ba-aa8e-4bb8-8231-c34965b450e1`):
   - resumo, descrição, status e responsável;
   - história/épico pai;
   - subtarefas e links de bloqueio.
   - Se a task for subtarefa, leia também a história pai: os critérios de aceitação costumam estar nela.
3. **Conferir:**
   - **Responsável é outra pessoa:** avise e pare. Quem troca é o PO.
   - **Bloqueada por issue não concluída:** avise e pergunte se segue mesmo assim.
4. **Ler só o necessário em `docs/`:**
   - a seção `US-NN` do `docs/BACKLOG.md`;
   - os `ADR-NNN` citados;
   - o `AGENTS.md` da pasta que será tocada.
   - Não carregue documentos inteiros.
5. **Branch.** Antes, verifique se a árvore está limpa (`git status`). Se não estiver, pergunte o que fazer. Depois:
   ```
   git switch main && git pull
   git switch -c SCRUM-NN-descricao-curta
   ```
6. **Jira.** Se o status for `A fazer`, mova para `Em andamento` (transição 21). Não comente nada ainda.
7. **Plano.** Entregue o plano e **espere aprovação antes de codar**. Ele deve ter:
   - **Entendimento:** a task em 2 linhas, com suas palavras.
   - **Critérios de aceitação:** copiados, cada um com "como vou verificar".
   - **Arquivos:** o que pretende criar ou mudar. Sinalize se tocar `shared/`, que é protegido.
   - **Passos:** pequenos e verificáveis.
   - **Perguntas de produto:** qualquer ambiguidade no critério vira pergunta para levar ao **Luiz (PO)**. Não decida sozinho.
   - **Riscos de invariante:** quais invariantes do `AGENTS.md` raiz esta task pode violar.

## Não faça

- Não comece a implementar no mesmo passo do plano.
- Não crie subtarefas no Jira. Se a task parecer grande demais, sugira à pessoa falar com o PO.
