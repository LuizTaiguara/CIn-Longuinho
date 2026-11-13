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
  - item encerrado com a fonte "terceiro" mostra **"encerrado segundo terceiro"**, e não só "encerrado" (US-04, US-10);
  - o texto original do e-mail aparece no item **só para quem entrou** com a conta do CIn, e já vem
    com telefones e e-mails mascarados pela API. Se ele chegar a uma sessão anônima, o bug é da API;
  - item marcado "revisar" mostra o selo.
- **Não há painel admin nem área do administrador.** O ator "administrador" não existe (R6).
  - O único login é **com a conta Google do CIn** (`@cin.ufpe.br`), para o autor gerir os próprios anúncios (US-15, ADR-010).
  - Não existe conta própria, senha nem tela de cadastro de usuário.
  - Autoria é verificada no servidor. O front só esconde botões; quem nega é a API, com 403.
- **Textos, telas e fluxos seguem os wireframes da UX** (F-04).
  - Mudar o que o usuário vê é decisão de produto: veja a seção "Decisões de produto" na raiz.
  - O catálogo é **uma lista única** com achados e perdidos juntos, e o filtro refina. Não há abas (US-04, decisão do PO em 25/10/2026).

## Comandos

Stack: **React + Vite**, com testes em **Vitest** + Testing Library (decisão de 13/11/2026). Rode
tudo de dentro de `site/`, com Node 20 ou mais novo.

| Para… | Comando |
|---|---|
| Instalar | `npm install` |
| Rodar com o mock local | `npm run dev` e abrir o endereço que aparecer (porta 5173) |
| Rodar contra uma API de verdade ou o mock oficial | `API_URL=http://localhost:8000 npm run dev` |
| Testar | `npm test` |
| Gerar a versão de produção | `npm run build` |

**Mock local (`site/mock/`).** Sem `API_URL`, o `npm run dev` responde `/api/itens` e
`/api/locais` com dados fictícios, imitando o servidor (busca sem acento, filtros, paginação).
É **temporário**: quando o mock oficial do contrato (SCRUM-67) existir, rode com `API_URL` e apague
a pasta.
