---
name: abrir-pr
description: Abre o pull request da branch atual ligado à task do Jira, sugere o revisor certo, comenta o link no Jira e move a task para "Em análise". Use quando a pessoa disser "terminei", "abrir PR", "mandar para revisão".
---

# /abrir-pr

## Passos

1. **Pré-checagem.** Se algo abaixo falhar, pare e diga o que falta.
   - A branch atual **não** é `main` e segue `SCRUM-NN-...`. Extraia o `SCRUM-NN`.
   - `git status` está limpo. Se houver mudança solta, pergunte se entra no commit.
   - Commits seguem `SCRUM-NN: verbo no imperativo`.
   - Testes e lint da pasta passam. Os comandos estão no `AGENTS.md` da pasta. Se ainda não existirem, diga isso.
2. **Autorrevisão.**
   - Rode o checklist de `/revisar-pr` sobre `git diff main...HEAD`.
   - Se achar violação de invariante, **pare e mostre**. Não abra PR quebrado.
3. **Revisor**, pela tabela de `docs/EQUIPE.md`, conforme as pastas tocadas no diff:
   - mexeu em `shared/` → Miguel, obrigatoriamente;
   - mexeu só em `docs/`, `AGENTS.md` ou `.agents/` → Luiz.
   - Se o usuário do GitHub do revisor ainda não estiver preenchido, diga quem é e peça para a pessoa marcar à mão.
4. **Push e PR.**
   ```
   git push -u origin HEAD
   gh pr create --base main --title "SCRUM-NN: <resumo>" --body-file <corpo>
   ```
   - O corpo segue `.github/pull_request_template.md`, preenchido, com o link do Jira.
   - Para adicionar o revisor: `--reviewer <usuario>`.
5. **Jira**, pelo MCP Atlassian (cloudId `66a6b7ba-aa8e-4bb8-8231-c34965b450e1`):
   - comente na task: `PR aberto: <url do PR>. Revisor: <nome>.`;
   - mova para `Em análise` (transição 31).
6. **Responda** com o link do PR e o que o revisor deve olhar com mais cuidado.

## Não faça

- Não faça merge, nem aprove o próprio PR.
- Não mova a task para `Concluído`. Isso é do PO, após o aceite.
- Não use `--force` em push.
