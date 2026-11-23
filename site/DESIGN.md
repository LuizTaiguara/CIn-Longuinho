---
name: CIn-Longuinho
description: Catálogo do que circula na lista de achados e perdidos do CIn-UFPE, montado como um espécime tipográfico em grade e lido no celular, de passagem.
colors:
  papel: "#FFFFFF"
  tinta: "#231F20"
  tinta-suave: "#5B5657"
  apagado: "#6E696A"
  vermelho: "#DB1E2F"
  vermelho-escuro: "#AF0421"
  vermelho-claro: "#FDF0F1"
  cinza: "#E0E1E0"
  quadricula: "#EDEDEC"
  chao-suave: "#F6F6F5"
typography:
  marca:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "-0.01em"
  display:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "clamp(34px, 9.4vw, 68px)"
    fontWeight: 700
    lineHeight: 0.94
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "clamp(28px, 7.4vw, 50px)"
    fontWeight: 700
    lineHeight: 0.98
    letterSpacing: "-0.015em"
  titulo-pagina:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "clamp(28px, 7vw, 44px)"
    fontWeight: 900
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  nome-do-objeto:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.12
    letterSpacing: "-0.005em"
  body:
    fontFamily: "'Hanken Grotesk', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
  botao:
    fontFamily: "Tektur, 'Hanken Grotesk', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.03em"
rounded:
  nenhum: "0px"
spacing:
  fio: "2px"
  celula: "13px"
  celula-dupla: "26px"
  largura: "1040px"
components:
  botao-primario:
    backgroundColor: "{colors.vermelho}"
    textColor: "{colors.papel}"
    typography: "{typography.botao}"
    rounded: "{rounded.nenhum}"
    padding: "0 16px"
    height: "44px"
  botao-primario-hover:
    backgroundColor: "{colors.vermelho-escuro}"
    textColor: "{colors.papel}"
  botao-secundario:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    typography: "{typography.botao}"
    rounded: "{rounded.nenhum}"
    padding: "0 16px"
    height: "44px"
  botao-secundario-hover:
    backgroundColor: "{colors.chao-suave}"
    textColor: "{colors.tinta}"
  botao-perigo:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.vermelho-escuro}"
    typography: "{typography.botao}"
    rounded: "{rounded.nenhum}"
    padding: "0 16px"
    height: "44px"
  botao-perigo-hover:
    backgroundColor: "{colors.vermelho-claro}"
    textColor: "{colors.vermelho-escuro}"
  menu-link:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.nenhum}"
    padding: "0 10px"
    height: "40px"
  menu-cadastrar:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
    rounded: "{rounded.nenhum}"
    padding: "0 10px"
    height: "40px"
  campo:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    typography: "{typography.body}"
    rounded: "{rounded.nenhum}"
    padding: "11px 12px"
  opcao:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.nenhum}"
    padding: "8px 10px"
    height: "44px"
  opcao-marcada:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
  linha-do-anuncio:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    padding: "11px 10px"
  linha-do-anuncio-foto-aberta:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
  cabecalho-das-colunas:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
    typography: "{typography.label}"
    padding: "9px 14px"
  etapa-atual:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
    typography: "{typography.label}"
  alerta:
    backgroundColor: "{colors.vermelho-claro}"
    textColor: "{colors.vermelho-escuro}"
    rounded: "{rounded.nenhum}"
    padding: "10px 12px"
---

# Design System: CIn-Longuinho

Registro do sistema visual "Grade de Crouwel", escolhido pelo PO em 23/11/2026 (SCRUM-47). Substitui por
inteiro o visual anterior (direção "crachá", com Figtree), que foi descartado e não serve de base. Este
arquivo descreve o que está construído em `src/estilos.css`, `src/componentes/Icone.jsx` e
`src/fontes/`; se divergir do código, o código vence e este arquivo é corrigido. Os títulos das oito seções
ficam em inglês porque o formato DESIGN.md exige esses nomes exatos.

## Overview

**Creative North Star: "O Espécime em Grade"**

O catálogo é um espécime tipográfico montado numa grade visível de 13px, na linha de Wim Crouwel: papel
branco com o quadriculado fino à mostra, fios de tinta de 2px fechando cada célula, letras de grade (Tektur)
para tudo o que nomeia e um grotesco neutro (Hanken Grotesk) para tudo o que se lê. Cada coisa na tela
ocupa células: a busca é uma fileira de células encaixadas, cada anúncio é uma linha da grade, a situação
é uma marca de célula, a trilha do item são três células.

A densidade é alta de propósito. A pessoa chega de passagem, no celular, querendo achar uma coisa; uma
lista densa de linhas, sem foto por padrão, deixa passar o olho por dezenas de anúncios em segundos. A
foto não é vitrine: aparece quando a pessoa pede, e a linha se inverte para mostrá-la. O vermelho do CIn é
raro e por isso grita: marca, ação principal, o tipo "Perdido" e uma única diagonal por tela, a rebeldia
que a grade permite.

O sistema recusa a grade de cartões com foto (cara de marketplace genérico), a tabela cinza de painel
administrativo e a cara de sistema da universidade. É plano, sem sombra e sem raio: profundidade vem de
inversão (tinta sobre papel vira papel sobre tinta), nunca de elevação.

**Key Characteristics:**
- Grade visível de 13px no fundo de toda tela; medidas de respiro em múltiplos dela.
- Fio de tinta de 2px fecha cada célula; nenhum canto arredondado.
- Duas famílias: Tektur (marca, títulos, rótulos, botões, em caixa-alta espaçada nos rótulos) e Hanken Grotesk (texto).
- Vermelho só na marca, na ação principal e no "Perdido", mais uma diagonal por tela.
- Situação como marca de célula (vazada, meio cheia, cheia com visto), sempre acompanhada de texto.
- Estado ativo é inversão para tinta cheia, não cor nova.
- Um único movimento de assinatura: a foto que desenrola.

## Colors

Paleta do Manual de Identidade Visual do CIn (vermelho, vermelho escuro, preto, cinza claro) estendida com
neutros quentes para texto secundário, quadriculado e chão; nenhum verde, amarelo ou azul de estado.

### Primary
- **Vermelho CIn** (vermelho): a cor da casa, usada com avareza. Pinta a sílaba "CIn" e o traço da marca, o fundo da ação principal (Buscar, Enviar, Entrar, a confirmação de um fluxo), o rótulo do tipo "Perdido", a diagonal da tela e o "3" da chamada do catálogo. Também é o sinal fino de instrumento: anel de foco (3px), cursor de texto, seleção de texto, o quadrado interno da opção marcada e o contorno interno da célula de busca em foco.
- **Vermelho Profundo** (vermelho-escuro): o vermelho de estado. Hover do botão primário, texto e borda do botão de perigo, mensagens de erro de campo, borda de campo inválido, título de estado de erro e a marcação "retida" em "Meus anúncios".
- **Rosado de Alerta** (vermelho-claro): fundo do alerta e do hover do botão de perigo. Nunca em superfície decorativa.

### Neutral
- **Papel** (papel): fundo de toda célula (cabeçalho, linhas, fichas, formulários, painéis) e texto sobre tinta.
- **Tinta** (tinta): texto principal, todos os fios de 2px, o fundo das células invertidas (linha com foto aberta, cabeçalho das colunas, etapa atual da trilha, opção marcada, botão "Cadastrar" do cabeçalho).
- **Tinta Suave** (tinta-suave): texto de apoio: subtítulo, rótulos dos campos e da ficha, idade do anúncio, contador, "desde…", placeholders, rodapé.
- **Grafite Apagado** (apagado): o que já acabou. Linhas de anúncios encerrados (com o nome riscado) e itens ocultos em "Meus anúncios".
- **Cinza CIn** (cinza): fundo de espera da foto (enquanto carrega ou quando não preenche) e hover do "Limpar filtros"; borda fina de 1px do texto original.
- **Quadrícula** (quadricula): só as linhas de 1px do quadriculado de 13px no fundo do `body`.
- **Chão Suave** (chao-suave): hover de botões secundários, links do menu e opções; fundo do texto original, da faixa "Limpar filtros", da lista de pendências e do brilho do esqueleto de carregamento.

### Named Rules
**A Regra do Vermelho.** Vermelho como superfície ou como cor de texto só em quatro lugares: a marca, a ação principal, o tipo "Perdido" e a diagonal. Fora disso, ele aparece apenas como sinal fino de instrumento (foco, cursor, seleção, opção marcada). Se uma tela nova pede vermelho em outro lugar, a resposta é tinta.

**A Regra da Inversão.** O que está ativo, selecionado ou aberto vira tinta cheia com texto papel. Não existe cor de "selecionado" nem azul de link: a inversão é o único destaque de estado.

**A Regra do Encerrado Apagado.** O que terminou desbota para o grafite apagado e tem o nome riscado; não some, não muda de cor de marca.

## Typography

**Display Font:** Tektur (com fallback Hanken Grotesk, system-ui, sans-serif)
**Body Font:** Hanken Grotesk (com fallback system-ui, -apple-system, Segoe UI, sans-serif)
**Label/Mono Font:** Tektur, em caixa-alta com espaçamento aberto

**Character:** Tektur é letra de grade, quadrada e técnica, com cantos chanfrados que conversam com as células; carrega a voz da marca e de tudo o que nomeia. Hanken Grotesk é neutro e legível em tamanho pequeno, e some atrás do conteúdo. As duas são fontes variáveis com licença SIL OFL 1.1, servidas pelo próprio site a partir de `src/fontes/` (recortes latin e latin-ext, `font-display: swap`), sem Google Fonts nem CDN.

### Hierarchy
- **Marca** (Tektur 900, 22px, 24px a partir de 760px, altura 1): o nome CIn-Longuinho no cabeçalho.
- **Display** (Tektur 700, clamp(34px, 9.4vw, 68px), 0.94, caixa-alta, -0.02em, até 14ch): a chamada do catálogo, "O seu item em 3 cliquinhos". Não é título semântico: o h1 do catálogo é oculto.
- **Headline** (Tektur 700, clamp(28px, 7.4vw, 50px), 0.98, caixa-alta, -0.015em): o nome do objeto na ficha do item.
- **Título de página** (Tektur 900, clamp(28px, 7vw, 44px), 1.05, -0.02em, até 20ch): h1 de Cadastrar, Meus anúncios, confirmação; estados vazios usam a mesma família em 800, clamp(22px, 5.6vw, 30px).
- **Title** (Tektur 800, 20px, 1.05, -0.01em): h2 dos blocos (Falar com quem anunciou, Texto original, ações do autor).
- **Nome do objeto** (Tektur 700, 17px, 19px a partir de 760px, 1.12): o nome de cada linha da lista, que é o link do anúncio.
- **Body** (Hanken Grotesk 400, 16px, 1.45): texto corrido; o local da linha em 500, 14px; a situação em 700, 13px; o subtítulo em 500, 14px, até 46ch; parágrafos de estado até 62ch.
- **Label** (Tektur 700, 11 a 13px, caixa-alta, 0.03 a 0.05em): tipo do anúncio, rótulos dos campos e da ficha, contagem de resultados, etapas da trilha (10px), paginação, voltar.
- **Botão** (Tektur 700, 14px, 1.1, caixa-alta, 0.03em): todos os botões e links com cara de botão; o menu usa 13px (11px abaixo de 760px).

### Named Rules
**A Regra das Duas Vozes.** Tektur nomeia (marca, títulos, rótulos, botões); Hanken Grotesk informa (texto, local, situação, campos). Texto corrido nunca em Tektur, rótulo nunca em Hanken.

**A Regra da Fonte da Casa.** Fonte nova só entra como arquivo em `src/fontes/`, com licença registrada no `LEIA-ME.md`. Nada carregado de serviço externo.

## Layout

Grade de 13px (a "célula") visível no fundo: duas camadas de `linear-gradient` de 1px na cor quadrícula,
repetidas a cada 13px no `body`. O conteúdo fica num contêiner de no máximo 1040px, centrado, com respiro
lateral de uma célula (13px) no celular e duas (26px) a partir de 760px; o pé da página guarda cinco a seis
células. O cabeçalho e o rodapé ocupam a largura toda, com o conteúdo interno alinhado ao contêiner.

- **Celular (padrão, 390px de referência):** busca com o campo de texto e o botão Buscar na primeira fileira em largura total, depois Tipo e Local lado a lado e Situação embaixo, tudo como células da mesma caixa. Cada anúncio é uma linha de duas colunas: 74px para tipo e idade, o resto para nome, local, situação e o botão "Ver foto".
- **A partir de 760px:** a busca vira uma única fileira (texto 2.2fr, três filtros 1fr). Cada linha da lista vira quatro células (132px tipo, 1.7fr objeto, 1.1fr local, 1.3fr situação) separadas por fios de 2px, sem cabeçalho de colunas (cada linha já diz tudo; barra de títulos puxaria para painel admin). "Ver foto" fica dentro da célula do objeto. A ficha do item passa a rótulos de 160px à esquerda dos valores.
- **A partir de 960px:** a página do item vira duas colunas (ficha à esquerda, lateral de 340px à direita, colada no topo ao rolar). Abaixo disso, a ordem é ficha, lateral (contato e ações), texto original.

Espaçamentos internos são pequenos e densos (9 a 14px dentro das células, 6 a 18px entre blocos); o ritmo
vem dos fios, não de espaço em branco.

### Named Rules
**A Regra da Célula.** Todo bloco é uma célula fechada por fio de 2px; blocos vizinhos compartilham o fio (um some para não dobrar a espessura). Elemento solto, sem célula, só o que é texto de apoio.

## Elevation & Depth

Sistema plano, sem nenhuma sombra de elevação. Profundidade e estado vêm de três recursos: o fio de
tinta que delimita, a inversão para tinta cheia (linha com foto aberta, etapa atual, opção marcada,
cabeçalho das colunas) e o chão suave no hover. O único `box-shadow` do sistema é um contorno interno de
3px em vermelho (`inset 0 0 0 3px`) na célula de busca e nos filtros em foco: substitui o anel de foco
onde o anel seria cortado pela caixa, e não é sombra.

### Named Rules
**A Regra do Papel Plano.** Nada flutua. Se algo precisa se destacar, ele se inverte ou ganha fio; nunca ganha sombra.

## Shapes

Ângulo reto em tudo (raio 0), inclusive opções de rádio e caixas de marcar, que são quadrados de 20px com
fio de 2px e um quadrado vermelho de 10px quando marcados. Bordas sólidas de 2px em tinta para células;
tracejado de 2px em tinta para o que é provisório ou pede atenção (campo de arquivo, nota "revisar",
confirmação de ação, lista de pendências). A única forma fora do ortogonal é a diagonal vermelha, uma
barra inclinada a 34°: na chamada do catálogo e no canto inferior direito do nome do objeto na ficha.

As marcas de situação (`Icone.jsx`) são células: **aberto** é um quadrado vazado, **reivindicado** é o
quadrado com a metade esquerda cheia, **encerrado** é o quadrado cheio com um visto em papel. Os demais
ícones (tipo, busca, local, setas, alerta, foto, removido) são desenhados no próprio projeto, sem
biblioteca, num quadro de 24 com traço de 2px, e saem sempre com `aria-hidden`: o texto ao lado é que diz
o que é.

### Named Rules
**A Regra de Uma Diagonal.** Cada tela tem no máximo uma diagonal vermelha. Ela é a rebeldia permitida pela grade; duas viram decoração.

**A Regra da Marca com Texto.** Situação nunca é só cor nem só ícone: a marca de célula vem sempre ao lado da palavra ("aberto", "reivindicado há 1 mês, retirada não confirmada", "encerrado segundo terceiro").

## Components

### Buttons
Caixas retas, firmes, em letra de grade caixa-alta.
- **Shape:** sem raio, fio de 2px em tinta, altura mínima de 44px, 16px de respiro lateral.
- **Primário:** fundo vermelho, texto papel. É a ação principal do bloco (Buscar, Enviar, Entrar com a conta do CIn, confirmar).
- **Hover / Focus:** hover escurece para o vermelho profundo em 0.15s; ao pressionar desce 1px; foco é anel vermelho de 3px afastado 2px. Desabilitado fica com 50% de opacidade.
- **Secundário:** fundo papel, texto tinta; hover em chão suave. Ações paralelas (cancelar, corrigir, abrir no Gmail, copiar).
- **Perigo:** fundo papel, borda e texto em vermelho profundo; hover em rosado de alerta. Só para remover/ocultar.
- **Link:** sem caixa, Hanken 600 sublinhado em 2px (o "Sair" do menu).
- **Largo:** variante de largura total com texto quebrando em duas linhas (o convite a entrar para falar com quem anunciou).

### Cabeçalho e navegação
- **Marca CIn-Longuinho:** só tipográfica, Tektur 900. "CIn" em vermelho, "Longuinho" em tinta, e o hífen desenhado como um traço vermelho de 0.5em por 0.24em (o hífen continua no texto, para o nome ser lido inteiro). Não é o logotipo do CIn nem da UFPE (ADR-011). O ícone da aba repete a ideia: quadrado com fio de tinta, um "C" vermelho e um "L" em tinta.
- **Menu:** links em células de 40px (38px no celular) com fio de 2px, Tektur 13px caixa-alta. "Cadastrar" é invertido (tinta cheia com o ícone de mais); os demais em papel com hover em chão suave. Página atual marcada por sublinhado vermelho de 3px.
- **Barra:** fundo papel, fio de 2px embaixo, quebra em duas linhas no celular.

### Busca em células
Um único bloco com fio de 2px, dividido em células por fios internos. Cada célula tem o rótulo em Tektur
11px caixa-alta na tinta suave e o valor embaixo. O campo de texto usa Hanken 500 a 18px, cursor vermelho,
e o botão Buscar vermelho ocupa a altura toda da célula. Os seletores são nativos sem aparência própria,
com uma seta de traço de 2px em tinta. Foco pinta o contorno interno vermelho de 3px na célula inteira.
"Limpar filtros" é uma faixa em chão suave na base do bloco.

### Linha do anúncio
O componente de assinatura. Cada anúncio é uma linha da lista (fio de 2px entre linhas):
- **Coluna do tipo:** "Achado"/"Perdido" em rótulo Tektur ("Perdido" em vermelho) e a idade ("há 3 meses") em Hanken 600, 12px, números tabulares; o selo "revisar" (rótulo Tektur 10px caixa-alta com ícone de alerta, num contorno de 1.5px na cor do texto) quando a classificação é de confiança média.
- **Corpo:** nome do objeto em Tektur 700 (a linha inteira do texto é clicável), local em Hanken 500, situação com a marca de célula e o texto, mais a localização declarada depois de um ponto.
- **"Ver foto":** só existe quando o anúncio tem foto. Botão secundário pequeno (40px, rótulo 11px) com o ícone de foto. Ao tocar, a linha inteira se inverte para tinta, o botão vira "Fechar foto" com contorno papel, e a foto desce em largura total por baixo da linha. A imagem só é baixada quando a pessoa pede. Sem foto, não há quadrado vazio nem coluna vazia: o botão simplesmente não aparece.
- **Encerrado:** a linha desbota para o grafite apagado e o nome fica riscado em 2px.
- **Desktop:** as mesmas partes viram quatro células com fios de 2px (tipo | objeto, com o "Ver foto" embaixo do nome | local | situação). Sem cabeçalho de colunas e sem coluna de foto: com quase nenhum anúncio com foto, ela seria uma fileira de células vazias.
- **Paginação:** célula de três partes coladas embaixo da lista (mais recentes, "Página 1 de 2", mais antigos); no celular o rótulo da página fica numa linha própria e os dois botões dividem a linha de baixo.

### Ficha do item
- **Faixa de cima:** tipo com ícone e selo, em célula própria.
- **Foto:** em largura total no topo da ficha (até 62vh no celular, 340px no desktop), sobre fundo cinza.
- **Nome:** headline Tektur caixa-alta, com a diagonal vermelha saindo do canto inferior direito.
- **Dados:** lista de rótulo e valor, cada par numa célula (rótulo acima no celular, coluna de 160px no desktop).
- **Trilha da situação:** três células iguais (aberto, reivindicado, encerrado) com rótulo Tektur 10px; só a atual se inverte para tinta. As outras não são pintadas, porque a declaração de desfecho pode pular "reivindicado". A frase da situação e o "desde…" ficam abaixo; no estado "aberto" a frase fica só para leitor de tela, já que a trilha diz o mesmo.
- **Blocos laterais:** "Falar com quem anunciou", ações do autor e texto original em células próprias; o texto original vem em Hanken 15px sobre chão suave com fio fino de 1px em cinza.

### Inputs / Fields
- **Style:** fio de 2px em tinta, sem raio, fundo papel, Hanken 16px, 11px por 12px de respiro. Rótulo acima em Tektur 12px caixa-alta. Áreas de texto com 120px mínimos e redimensionamento vertical.
- **Focus:** anel vermelho de 3px afastado 2px; cursor vermelho.
- **Error:** borda em vermelho profundo e mensagem em Hanken 700, 14px, vermelho profundo, abaixo do campo; contador de caracteres em tinta suave, alinhado à direita.
- **Opções (tipo, locais):** grupo sem moldura própria, só a legenda; cada opção é uma célula de 44px com fio de 2px e um quadrado de marcar; marcada, a célula se inverte para tinta e o quadrado interno fica vermelho.
- **Campo de arquivo:** célula tracejada de 2px com um botão secundário desenhado ("Escolher foto", depois "Trocar foto") e o nome do arquivo em tinta suave; o input nativo cobre a célula toda, invisível, e o foco desenha o anel vermelho na célula.

### Estados e avisos
- **Carregando:** esqueleto de linhas de 86px com um brilho de chão suave varrendo (1.4s, contínuo).
- **Vazio / sem resultado / erro:** célula com título Tektur 800 (em vermelho profundo no erro) e parágrafos curtos, com o botão de saída (limpar filtros, tentar de novo).
- **Alerta:** fio de 2px em vermelho profundo sobre rosado de alerta, texto em vermelho profundo 600.
- **Confirmação e pendência:** célula tracejada; pendência sobre chão suave.

### Movimento
Um só movimento de assinatura: ao abrir a foto, ela **desenrola** de cima para baixo (`clip-path` de `inset(0 0 100% 0)` a `inset(0)`, 0.45s, curva de saída `cubic-bezier(0.16, 1, 0.3, 1)`), como uma célula se abrindo. O resto é retorno de estado curto: fundo e cor de botões, opções e linhas em 0.15 a 0.2s, o quadrado da opção marcada crescendo em 0.12s, e o brilho do esqueleto. Com `prefers-reduced-motion: reduce`, toda animação e transição é desligada.

## Do's and Don'ts

### Do:
- **Faça** cada bloco novo como célula: fio de 2px em tinta, raio 0, fundo papel, encaixado no contêiner de 1040px e na grade de 13px.
- **Faça** títulos, rótulos e botões em Tektur (rótulos em caixa-alta com 0.03 a 0.05em) e todo texto corrido em Hanken Grotesk.
- **Faça** o estado ativo, aberto ou selecionado por inversão para tinta com texto papel.
- **Faça** cada situação com a marca de célula (vazada, meio cheia, cheia com visto) e a palavra ao lado.
- **Faça** a foto aparecer só quando pedida ou na ficha do item, e carregue a imagem só quando ela for mostrada.
- **Faça** no máximo uma diagonal vermelha (barra inclinada a 34°) por tela.
- **Faça** ícones novos no `Icone.jsx`, no quadro de 24 com traço de 2px, sempre com `aria-hidden` e texto ao lado.
- **Faça** qualquer movimento novo respeitar `prefers-reduced-motion`; o desenrolar da foto é o único movimento de assinatura.

### Don't:
- **Não** use vermelho fora da marca, da ação principal, do tipo "Perdido" e da diagonal (exceto como sinal de foco, cursor, seleção e opção marcada).
- **Não** monte a lista como grade de cartões com foto, e não desenhe quadrado vazio ou placeholder de "sem foto".
- **Não** ponha sobretítulo (eyebrow) acima de título.
- **Não** use raio de canto, sombra de elevação nem gradiente decorativo.
- **Não** carregue fonte do Google Fonts nem de CDN; as fontes moram em `src/fontes/`.
- **Não** use o logotipo do CIn nem o da UFPE; a marca é só tipográfica, CIn-Longuinho (ADR-011).
- **Não** diferencie estado só por cor: toda situação tem marca e texto.
- **Não** faça tabela cinza de painel, cara de sistema da universidade, mascote nem ilustração fofa.
- **Não** reaproveite nada do visual "crachá" (Figtree, cartões arredondados, verdes e amarelos de estado).
