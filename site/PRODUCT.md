# Produto

<!-- impeccable:product-schema 1 -->

Registro de produto usado pela skill de design. Não é fonte de verdade: resume o `AGENTS.md` da raiz, o
`site/AGENTS.md` e o `docs/BACKLOG.md`. Se divergir deles, eles vencem. Escrito em 22/11/2026, numa rodada
sem entrevista: o que não vem citado de um documento está marcado como *(inferido)*.

## Platform

web

## Users

- Alunos, professores e funcionários do Centro de Informática da UFPE (US-04).
- Quase sempre no celular, entre uma aula e outra, com pouca atenção disponível (briefing do PO, 22/11/2026).
- Dois trabalhos: achar "minha garrafa azul" no que já foi anunciado, e avisar que achou ou perdeu algo.
- Quem anunciou volta para gerir o próprio anúncio: corrigir, marcar como devolvido, remover (US-15).
- Ler o catálogo não exige login. Só entra quem tem conta Google `@cin.ufpe.br` (ADR-010).

## Product Purpose

Catálogo pesquisável do que circula na lista de e-mail `achados-perdidos@cin.ufpe.br`. A lista já existe e
funciona; o sistema preenche lacunas desse processo comunitário e não o substitui. Deu certo quando a pessoa
encontra o anúncio certo em segundos e sabe, sem ambiguidade, em que pé ele está.

## Positioning

Não há dono do processo nem custódia institucional (R6, ADR-011). O catálogo não promete guardar nem
devolver nada: mostra o que foi anunciado e o que se sabe, dizendo de onde veio cada informação.

## Operating Context

- A fonte é a lista de e-mail. Um worker lê, classifica e extrai; o site só consome a API REST.
- Quem cadastra pelo site recebe um e-mail pronto para mandar à lista, com um código `[AP-XXXXXX]` no assunto (US-07).
- O contato com quem anunciou é por botão: a mensagem vai por e-mail e o endereço nunca aparece (US-05).
- Locais são os do prédio: Grad 1 a 5, laboratórios, anfiteatro, salas como "E112".

## Capabilities and Constraints

- **Lista única**, com achados e perdidos juntos, e filtro por tipo, local e situação. Sem abas (US-04).
- **Situação com honestidade:** `aberto`; `reivindicado há …, retirada não confirmada`; `encerrado`;
  `encerrado segundo terceiro`. O selo "revisar" marca classificação automática de confiança média.
- **Nenhum e-mail de pessoa na tela.** O texto original só aparece para quem entrou, já mascarado pela API.
- **O front não filtra visibilidade.** Quem decide o que aparece é a API.
- **Sem tela de administrador.** O ator "administrador" não existe.
- **Sem prazo de guarda.** Nada expira por tempo.
- Remover é ocultar, e não pode ser desfeito pelo site. O rodapé traz o e-mail do canal humano de remoção (US-09).
- Telas: catálogo, item, login, cadastrar, "Meus anúncios".
- Stack: React + Vite + React Router, CSS puro, testes em Vitest.

## Brand Commitments

- O sistema **não é institucional**: usa as cores do CIn-UFPE, mas não o logotipo do CIn nem o da UFPE (ADR-011).
- Paleta do Manual de Identidade Visual do CIn (ago/2020): vermelho `#DB1E2F` (primária), vermelho escuro
  `#AF0421`, preto `#231F20`, cinza claro `#E0E1E0`. Cores complementares, com moderação, para os estados.
- A fonte oficial (Proxima Nova) é paga. Usa-se uma gratuita parecida, servida pelo próprio site.
- Tudo em português. Tom direto, de colega para colega, sem jargão de sistema *(inferido dos textos atuais)*.

## Evidence on Hand

- Corpus de 70 mensagens reais anonimizadas (`worker/corpus/`), com nomes fictícios `fic.*`.
- Não há fotos reais: as do corpus foram trocadas por uma imagem cinza. Não inventar fotos de objetos.
- Não há números de uso nem depoimentos. Não inventar.

## Product Principles

1. **Honestidade antes de conforto.** Dizer o que se sabe e de onde veio; campo vazio é melhor que campo errado.
2. **Privacidade no servidor.** A tela nunca mostra nem esconde por conta própria.
3. **Preencher lacunas, não substituir.** A lista continua sendo o processo; o site aponta para ela.
4. **Sobreviver ao abandono.** Nada que dependa de alguém cuidando: sem painel, sem moderação, sem prazo.
5. **Ferramenta, não vitrine.** Leitura rápida no celular vale mais que expressão visual.

## Accessibility & Inclusion

- Contraste WCAG AA. Estado nunca é diferenciado só pela cor.
- Foco visível, labels em todos os campos, navegação por teclado e respeito a `prefers-reduced-motion`.
