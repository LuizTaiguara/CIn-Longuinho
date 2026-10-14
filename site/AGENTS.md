# site/ — regras do site / catálogo (JavaScript)

Vale além do `AGENTS.md` da raiz. Front: Pedro e Rafael. UX: Klarissa.

## O que é

- Aplicação web que fica de pé.
- Consome **somente a API REST** definida em `shared/`.
- Nunca acessa o banco direto e nunca chama o worker.

## Regras

- **Trabalhe contra o contrato e o mock**, não contra o código do backend.
  - Se o mock não tem o que você precisa, a mudança é no contrato (ver `shared/AGENTS.md`). Não faça gambiarra no front.
- **Não filtre visibilidade no cliente.** Se um item em quarentena ou oculto chegou ao front, o bug é da API.
  - Aponte o bug. Não esconda no front.
- **Não existe campo de e-mail para exibir.** O contato com quem anunciou é por botão que encaminha a mensagem.
- **O estado aparece com honestidade:**
  - `reivindicado` mostra **há quanto tempo** ("reivindicado há 3 semanas, retirada não confirmada");
  - o texto original do e-mail fica sempre visível no item;
  - item marcado "revisar" mostra o selo.
- **Não há painel admin nem área do administrador.** O ator "administrador" não existe (R6).
  - O único login é **com a conta Google do CIn** (`@cin.ufpe.br`), para o autor gerir os próprios anúncios (US-15, ADR-010).
  - Não existe conta própria, senha nem tela de cadastro de usuário.
  - Autoria é verificada no servidor. O front só esconde botões; quem nega é a API, com 403.
- **Textos, telas e fluxos seguem os wireframes da UX** (F-04).
  - Mudar o que o usuário vê é decisão de produto: veja a seção "Decisões de produto" na raiz.
  - Ainda pendente com o PO e a UI: abas separadas para achados e perdidos, ou lista única com filtro?

## Comandos

_A definir quando existir código (Sprint 0)._ Preencha aqui: instalar, rodar com mock,
rodar testes, lint.
