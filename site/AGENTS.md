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
- **O visual segue o `site/DESIGN.md`.** Em 22/11/2026 o PO mandou refazer as telas do zero, com as
  cores do CIn-UFPE, sem seguir os wireframes da UX (SCRUM-47). Os fluxos e os textos exigidos pelos
  critérios do `docs/BACKLOG.md` continuam valendo.
  - Cores, fonte, componentes e o que não fazer estão no `DESIGN.md`. Tela nova usa o que já existe lá.
  - O sistema não é institucional (ADR-011): usa as cores do CIn, mas **não** o logotipo do CIn nem o da UFPE.
  - A fonte (Figtree) é servida pelo próprio site, via `@fontsource/figtree`. Nada de Google Fonts nem de CDN.
  - Estado nunca é diferenciado só pela cor: cada situação tem desenho e texto.
  - Mudar o que o usuário vê é decisão de produto: veja a seção "Decisões de produto" na raiz.
  - O catálogo é **uma lista única** com achados e perdidos juntos, e o filtro refina. Não há abas (US-04, decisão do PO em 25/10/2026).

## Comandos

Stack: **React + Vite + React Router**, com testes em **Vitest** + Testing Library (decisão de
13/11/2026). Rode tudo de dentro de `site/`, com Node 20 ou mais novo.

| Para… | Comando |
|---|---|
| Instalar | `npm ci` |
| Rodar com o mock local | `npm run dev` e abrir o endereço que aparecer (porta 5173) |
| Rodar contra a API de verdade | `API_URL=http://localhost:8000 npm run dev` |
| Testar | `npm test` |
| Gerar a versão de produção | `npm run build` (sai em `site/dist/`, que não é commitado) |
| Subir a versão de produção no Docker | `docker compose up -d --build api site`, da raiz (porta 8080) |

**Variáveis.** O Vite lê o `.env` da raiz do repositório. Só as que começam com `VITE_` chegam ao
navegador, então nenhuma delas pode ter segredo. Hoje há uma: `VITE_EMAIL_REMOCAO`, o endereço do
rodapé (US-09).

**Docker (`site/Dockerfile`, `site/nginx.conf`).** A imagem gera o build e serve com nginx, que
repassa `/api/` para o serviço `api` do compose: site e API ficam na mesma origem e o cookie de
sessão vale para os dois. `VITE_EMAIL_REMOCAO` entra como argumento de build (mudou o valor,
reconstrua com `--build`). O nginx sobe mesmo com a API parada; aí `/api` responde 502 e o
catálogo mostra a mensagem de erro. Para o login voltar ao site, a API precisa de
`SITE_URL=http://localhost:8080`.

**Mock local (`site/mock/`).** Sem `API_URL`, o `npm run dev` responde as 14 rotas de `/api` do
contrato com dados fictícios, imitando as regras do servidor: busca sem acento, filtros, paginação,
404 para item oculto, texto original só com sessão, `pode_gerir`, 401 e 403. As regras ficam em
`mock/rotas.js` (testadas em `mock/servidorLocal.test.js`) e os dados em `mock/dados.js`.
O mock oficial da SCRUM-67 foi dispensado: a API de verdade substitui este mock, que é descartável.

- **Login simulado:** "Entrar com a conta do CIn" grava o cookie `sessao_mock` e volta para onde
  você estava. "Sair" apaga o cookie. A sessão simulada é autora de alguns itens fictícios, tem uma
  mensagem retida e um item oculto, para dar para ver "Meus anúncios" inteiro.
- **Estados para ver no navegador:**

| Variável | Efeito |
|---|---|
| `MOCK_VAZIO=1` | catálogo sem nenhum item (primeira execução) |
| `MOCK_FALHA=1` | API fora do ar: tudo responde 503 |
| `MOCK_CONTATO_FALHA=1` | o contato com quem anunciou responde 502 |
| `MOCK_LOGIN_FORA=1` | o login volta como conta de fora do CIn |

A busca sem resultado aparece com qualquer termo que não exista, por exemplo `?texto=guarda-chuva`.
Os dados do mock mudam em memória (corrigir, encerrar, ocultar, cadastrar) e voltam ao início
quando o `npm run dev` é reiniciado.
