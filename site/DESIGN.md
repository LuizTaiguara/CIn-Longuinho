---
name: Achados e Perdidos do CIn
description: Catálogo do que circula na lista de achados e perdidos do CIn-UFPE, lido no celular entre uma aula e outra.
colors:
  vermelho: "#DB1E2F"
  vermelho-escuro: "#AF0421"
  preto: "#231F20"
  cinza: "#E0E1E0"
  chao: "#F3F3F2"
  papel: "#FFFFFF"
  tinta-suave: "#5B5657"
  borda: "#D3D4D3"
  borda-campo: "#7B7677"
  achado: "#0A6B5E"
  achado-claro: "#E3F1EE"
  achado-tinta: "#084F46"
  reivindicado: "#8A4B00"
  atencao: "#FFD166"
  atencao-claro: "#FFF4D9"
  atencao-tinta: "#6B3A00"
  atencao-borda: "#B77900"
  erro-claro: "#FCE9EB"
  erro-tinta: "#7D0318"
typography:
  headline:
    fontFamily: "Figtree, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Figtree, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Figtree, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Figtree, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 800
    lineHeight: 1.3
    letterSpacing: "0.06em"
rounded:
  campo: "8px"
  cartao: "12px"
  pilula: "999px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "14px"
  lg: "18px"
  xl: "32px"
components:
  botao-principal:
    backgroundColor: "{colors.vermelho}"
    textColor: "{colors.papel}"
    rounded: "{rounded.campo}"
    padding: "10px 18px"
    height: "48px"
  botao-principal-hover:
    backgroundColor: "{colors.vermelho-escuro}"
  botao-secundario:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.preto}"
    rounded: "{rounded.campo}"
    padding: "10px 18px"
    height: "48px"
  botao-sem-volta:
    textColor: "{colors.preto}"
    rounded: "{rounded.campo}"
  campo:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.preto}"
    rounded: "{rounded.campo}"
    padding: "10px 12px"
    height: "48px"
  cracha:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.preto}"
    rounded: "{rounded.cartao}"
  faixa-achado:
    backgroundColor: "{colors.achado}"
    textColor: "{colors.papel}"
    typography: "{typography.label}"
  faixa-perdido:
    backgroundColor: "{colors.preto}"
    textColor: "{colors.papel}"
    typography: "{typography.label}"
  selo-revisar:
    backgroundColor: "{colors.atencao}"
    textColor: "{colors.preto}"
    rounded: "{rounded.pilula}"
---

# Design System: Achados e Perdidos do CIn

Os títulos das seções ficam em inglês porque são os do formato DESIGN.md, que outras ferramentas leem.
O resto é em português, como todo o repositório. A fonte de verdade dos valores é `src/estilos.css`.

## Overview

**Creative North Star: "O crachá"**

Cada anúncio é um crachá. Uma faixa no topo diz o papel (Achado ou Perdido), o nome do objeto vem grande,
como o nome de uma pessoa no crachá, e a situação é a linha impressa embaixo, sempre no mesmo lugar. O
crachá é um objeto que todo mundo no CIn carrega, e é também um dos objetos que mais aparecem na lista.

O site é ferramenta, não vitrine. Quem usa está no celular, num corredor, com meio minuto. Por isso o
sistema empresta do crachá só quatro coisas: a tipografia, a paleta, a densidade e a faixa. O resto são
controles comuns da web, que a pessoa já sabe usar: campo de busca, `select`, botão, caixa de marcar.

O sistema recusa duas saídas fáceis: a grade de cartões com miniatura e ilustração simpática, e a tabela
cinza de painel administrativo. Não há ilustração, não há sombra e não há logotipo do CIn nem da UFPE
(o sistema não é institucional, ADR-011).

**Key Characteristics:**
- Cabeçalho em duas faixas de vermelho; o vermelho não aparece em mais nada além da ação principal.
- Registros brancos com borda fina sobre um chão cinza muito claro.
- Faixa cheia para anúncio em andamento, faixa vazada para anúncio encerrado ou removido.
- Situação com desenho próprio e texto, nunca só cor.
- Uma família tipográfica só, com pesos 400, 600, 700 e 800.
- Claro, sem modo escuro: o uso é de dia, em corredor e sala de aula.

## Colors

A paleta é a do Manual de Identidade Visual do CIn (ago/2020), mais poucas cores de apoio para tipo e estado.

### Primary
- **Vermelho CIn** (#DB1E2F): a faixa principal do cabeçalho e o botão da ação principal de cada tela
  (Buscar, Publicar anúncio, Enviar mensagem, Salvar correção). Também marca seleção de texto, cursor e
  caixas marcadas.
- **Vermelho escuro CIn** (#AF0421): a segunda faixa do cabeçalho, o estado de passar o mouse do botão
  principal, links e textos de erro.

### Secondary
- **Verde-petróleo do achado** (#0A6B5E): só a faixa de anúncio achado e os avisos de sucesso. É a cor
  complementar do vermelho, para as duas nunca se confundirem.

### Tertiary
- **Âmbar de atenção** (#FFD166, com #FFF4D9 de fundo e #6B3A00 de texto): o selo "revisar", as confirmações
  antes de uma ação sem volta, "ainda não foi para a lista" e a mensagem que não entrou no catálogo.
- **Castanho do reivindicado** (#8A4B00): só o texto da situação "reivindicado há …".

### Neutral
- **Preto CIn** (#231F20): texto, a faixa de anúncio perdido, bordas de botão secundário e o anel de foco.
- **Tinta suave** (#5B5657): texto de apoio (local, datas, avisos) e a situação "encerrado".
- **Cinza claro CIn** (#E0E1E0): botão desabilitado. As bordas de cartão usam um tom vizinho, #D3D4D3.
- **Chão** (#F3F3F2): o fundo da página. **Papel** (#FFFFFF): o fundo de cartões e campos.
- **Borda de campo** (#7B7677): contorno de campos de formulário, com contraste de 4,5:1 sobre o papel.

### Named Rules
**A regra do vermelho com um trabalho só.** O vermelho é do cabeçalho e da ação principal. Não marca tipo,
não marca estado e não decora. Uma tela tem no máximo um botão vermelho por bloco.

**A regra de nunca só a cor.** Tipo e situação têm sempre três sinais: palavra, desenho e cor. Achado é uma
etiqueta, perdido é uma lupa; aberto é um anel, reivindicado é meio disco, encerrado é um disco com visto.

**Contraste conferido (WCAG AA).** Branco no vermelho 4,95:1; branco no vermelho escuro 7,3:1; branco na
faixa de achado 6,4:1; tinta suave no papel 7,2:1 e no chão 6,5:1; reivindicado no papel 6,8:1; texto de
erro 9,5:1; texto do selo "revisar" 11,3:1. Sobre o vermelho, o texto é sempre branco puro, nunca cinza.

## Typography

**Display Font:** Figtree (com system-ui, Segoe UI, Roboto)
**Body Font:** Figtree

**Character:** uma sem serifa geométrica e amigável, próxima da Proxima Nova do manual do CIn, que é paga.
É servida pelo próprio site, pelo pacote `@fontsource/figtree` (só o recorte latino, quatro pesos), sem
Google Fonts nem CDN.

### Hierarchy
- **Headline** (800, 1.625rem no celular e 2rem a partir de 600px, 1.15): o nome do objeto na página do
  item e o título das telas de cadastro e "Meus anúncios".
- **Title** (700, 1.1875rem, 1.25): o nome do objeto no crachá da lista. Títulos de bloco usam 1.125rem.
- **Body** (400, 1rem, 1.5): texto corrido. O texto original do e-mail fica em no máximo 72 caracteres por linha.
- **Label** (800, 0.8125rem, 0.06em, maiúsculas): só o tipo na faixa do crachá. Rótulos de campo usam
  0.9375rem em peso 600, sem maiúsculas.

### Named Rules
**A regra da escala fixa.** Tamanhos em `rem`, trocados por ponto de quebra. Nada de `clamp` nem de fonte
fluida: é ferramenta, e o texto não deve mudar de tamanho ao redimensionar um painel.

**A regra dos números alinhados.** Datas, contadores e a contagem de anúncios usam `tabular-nums`.

## Layout

Pensado primeiro para 390px. O conteúdo tem no máximo 1120px, com margem de 16px no celular e 24px a partir
de 600px.

- **Cabeçalho.** No celular são duas faixas: a vermelha com o nome e a frase do site, e a vermelho-escura
  com "Cadastrar" e a conta. A partir de 900px vira uma faixa só, com a escura reduzida a um filete embaixo.
- **Catálogo.** No celular, a busca vem primeiro: campo e botão, tipo em linha inteira, local e situação
  lado a lado, depois a lista. De 600px a 899px os três filtros ficam numa linha. A partir de 900px a busca
  vira uma coluna fixa de 300px à esquerda, que acompanha a rolagem, e a lista fica à direita.
- **Item.** Uma coluna no celular: ficha, texto original, contato ou ações do autor. A partir de 900px, a
  ficha e o texto ficam à esquerda e o contato ou as ações numa coluna de 360px à direita, onde as opções
  de formulário ficam sempre em uma coluna.
- **Paginação.** No celular, o "Página 1 de 2" fica numa linha e os dois botões dividem a de baixo.
- **Formulários.** Opções em uma coluna no celular e em duas a partir de 600px. Botões empilhados abaixo de
  480px, lado a lado acima disso.
- **Ritmo.** Espaços de 6, 10, 14 e 18px dentro dos blocos; 12 a 16px entre cartões; 32px entre colunas.
  Toda área de toque tem pelo menos 44px de altura; campos e botões têm 48px.

## Elevation & Depth

Não há sombra em lugar nenhum. A profundidade vem de duas camadas de tom (chão cinza claro e papel branco)
e de uma borda de 1px. Passar o mouse sobre um crachá escurece a borda; nada levanta.

### Named Rules
**A regra do plano.** Se um bloco precisa se destacar, ele ganha borda mais escura ou fundo tingido. Nunca sombra.

## Shapes

Cantos de 12px em cartões e blocos, 8px em campos e botões, e pílula só em controles pequenos (o selo
"revisar" e o "Cadastrar" do cabeçalho). O picote, uma linha tracejada de 1px, separa a situação do resto
do crachá e os campos da ficha: é o único ornamento, e vem do próprio crachá. Ícones são desenhados em
`src/componentes/Icone.jsx`, com traço de 2px e pontas arredondadas, sempre com um texto ao lado.

## Components

### Crachá (o registro de um anúncio)
- **Estrutura:** faixa do tipo (ícone, "ACHADO" ou "PERDIDO", selo "revisar" quando houver, e a data à
  direita); nome do objeto; local com o ícone de alfinete; picote; situação.
- **Local:** tinta cheia e peso 600, com só o alfinete em tinta suave. É por ele que a pessoa se orienta.
- **Faixa:** verde-petróleo para achado, preto para perdido, texto branco. Anúncio encerrado ou removido
  tem a faixa **vazada**: fundo branco, texto na cor do tipo e uma linha embaixo.
- **Situação:** peso 700, com o desenho da situação à esquerda. "aberto" em preto, "reivindicado há …,
  retirada não confirmada" em castanho, "encerrado" e "encerrado segundo terceiro" em tinta suave. Onde o
  objeto está agora vem na mesma linha, em peso 400.
- **Comportamento:** na lista, o cartão inteiro é clicável (o link do nome se estica por cima). O foco do
  teclado contorna o cartão todo.
- **Nada só no `title`:** o celular não tem "passar o mouse". Na página do item, a explicação do selo
  "revisar" e o "desde …" da situação aparecem escritos.
- **Variações:** a ficha da página do item é o mesmo crachá, maior. Em "Meus anúncios", a mensagem que não
  entrou no catálogo tem faixa âmbar com o motivo, e o anúncio que ainda não foi para a lista ganha uma
  aba âmbar colada embaixo.

### Buttons
- **Shape:** 8px de raio, 48px de altura, peso 700.
- **Primary:** fundo vermelho, texto branco. Um por bloco.
- **Hover / Focus:** o fundo vai a vermelho escuro em 160ms. O foco é um anel preto de 3px, afastado 2px
  (branco quando o botão está no cabeçalho).
- **Secondary:** fundo branco, borda e texto pretos. **Sem volta:** "Remover do catálogo" é um botão de
  texto preto sublinhado, o mais discreto do bloco, e sempre passa por uma confirmação. Ele não usa
  vermelho. **Link:** "Sair" e "Limpar filtros" são botões com cara de link sublinhado.
- **Ordem nas ações do autor:** "Marcar como devolvido" (principal), "Corrigir" (secundário), "Remover do
  catálogo" (sem volta).
- **Disabled:** fundo cinza claro, texto cinza, sem mudança ao passar o mouse.

### Chips
- **Selo "revisar":** pílula âmbar com ícone de alerta e texto preto. Fica na faixa, ao lado do tipo,
  porque é do tipo que ele fala. A explicação completa está no `title` e no texto para leitor de tela.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** papel branco sobre o chão.
- **Shadow Strategy:** nenhuma (ver Elevation & Depth).
- **Border:** 1px #D3D4D3. Bloco de erro: 1,5px vermelho escuro.
- **Internal Padding:** 14px no crachá da lista, 18px nos blocos, 24px na ficha a partir de 600px.

### Inputs / Fields
- **Style:** borda de 1,5px em #7B7677, fundo branco, 8px de raio, 48px de altura, rótulo sempre visível acima.
- **Focus:** o mesmo anel preto de 3px dos botões.
- **Error:** borda de 2px em vermelho escuro e a mensagem logo abaixo, em vermelho escuro e peso 600.
- **Opções:** cada caixa de marcar ou botão de rádio é uma linha inteira clicável de 48px. Marcada, ganha
  borda preta, fundo do chão e peso 600.

### Avisos
- **Erro** (`.alerta`): fundo rosado, borda vermelho-escura. **Sucesso** (`role="status"`): fundo verde
  claro, borda verde-petróleo. **Confirmação** antes de ação sem volta: fundo âmbar claro, com os dois
  botões dentro. Nenhuma confirmação usa janela modal.
- **Carregando:** texto mais três crachás em esqueleto. **Vazio e erro:** um bloco com título, explicação
  e um botão para sair dali.

### Movimento
- Transições de 160ms em cor e borda. Avisos, confirmações e formulários que se abrem surgem em 220ms.
- Com `prefers-reduced-motion`, tudo isso é desligado e o esqueleto fica parado.

## Do's and Don'ts

**Faça**
- Use o crachá para todo registro de anúncio, em qualquer tela nova.
- Mantenha a situação na última linha do crachá, com desenho e texto.
- Escreva os estados como o `site/AGENTS.md` manda: "reivindicado há …, retirada não confirmada",
  "encerrado segundo terceiro", selo "revisar".
- Deixe o rótulo de cada campo visível, acima do campo.
- Confira o contraste de qualquer cor nova (mínimo 4,5:1 para texto).

**Não faça**
- Não use o logotipo do CIn nem o da UFPE.
- Não use vermelho para marcar tipo ou estado, nem como enfeite.
- Não diferencie estado só pela cor.
- Não adicione sombra, degradê, vidro fosco nem ilustração.
- Não use barra colorida numa lateral do cartão: a faixa do crachá é o topo inteiro e carrega texto.
- Não troque a lista única por abas.
- Não mostre e-mail de pessoa, e não esconda nem filtre no site o que a API mandou.
- Não carregue fonte de fora do site.
