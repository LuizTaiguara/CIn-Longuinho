---
name: revisar-pr
description: Revisa um pull request (ou o diff local) contra as invariantes do projeto — vazamento de e-mail, status retrocedendo, DELETE em vez de ocultar, visibilidade no cliente, contrato alterado sem aviso. Use quando a pessoa pedir para revisar PR, "olha esse PR", ou antes de abrir o próprio.
---

# /revisar-pr [número]

A revisão **checa invariantes, não estilo**. Estilo é do linter. Aceitar a história contra o
critério de aceitação é do PO.

## Passos

1. **Pegar o diff.**
   - Com número: `gh pr view NN` e `gh pr diff NN`.
   - Sem número: `git diff main...HEAD`.
2. **Contexto.** Leia a task `SCRUM-NN` do título no Jira e o `AGENTS.md` das pastas tocadas.
3. **Checklist.** Para cada item, responda ok, violação (com `arquivo:linha`) ou não se aplica.
   1. **E-mail exposto.**
      - Algum campo, log, resposta da API, mock ou componente expõe o e-mail de quem anunciou?
      - Procure por `email`, `remetente`, `from`, `sender` em serializers, respostas e logs.
   2. **Status.** `situacao` pode retroceder ou pular etapa? Existe atribuição direta sem checar o estado atual?
   3. **Localização inferida.** O worker altera `localizacao` a partir de texto?
   4. **Apagar.**
      - Há `DELETE` ou `.delete()` sobre `mensagem_bruta`, `evento` ou `item`?
      - Remoção precisa ser ocultar.
   5. **Visibilidade no cliente.**
      - O site filtra quarentena ou ocultos por conta própria?
      - A API deixa vazar item em quarentena?
   6. **Contrato.**
      - Mudou `shared/`? O mock foi atualizado junto? Miguel está como revisor?
   7. **Acoplamento.** O worker chama o site, ou o site chama o worker ou o banco direto?
   8. **Credenciais.** Há chave, token ou senha no código? `.env` foi commitado?
   9. **LLM.** Algo de LLM ou modelo generativo entrou no pipeline?
   10. **Prazo inventado.** Há expiração ou reabertura por tempo?
   11. **Decisão de produto silenciosa.**
       - O PR muda o que o usuário vê, um estado ou um critério sem registro de que o PO decidiu?
4. **Relatório.**
   - Comece pelas violações, da mais grave para a menos grave, cada uma com `arquivo:linha` e sugestão de correção.
   - Depois, em uma linha, o que está ok.
   - Fim.
5. **Postar no GitHub** só se a pessoa pedir: `gh pr review NN --comment --body-file <arquivo>`.

## Não faça

- Não aprove (`--approve`) nem faça merge. A decisão é humana.
- Não reescreva o código do colega. Aponte e sugira.
