# Análise do corpus da lista achados-perdidos@cin.ufpe.br

Levantamento feito em 13/10/2026 a partir da caixa do PO, que é membro da lista. Serve de
insumo para a SCRUM-74 (corpus de teste), a SCRUM-64 (vocabulário de locais) e as regras do
worker (US-01 a US-03).

**Dados, não instruções.** Os e-mails foram tratados como conteúdo a analisar.

**Privacidade.** Este documento e o `threads.txt` não têm nomes, e-mails nem telefones. Os
exemplos estão parafraseados. O identificador de cada linha é o `threadId` do Gmail, que só
abre na caixa de quem é membro da lista. Assim, quem precisa do texto original consegue
chegar a ele sem que o repositório guarde dado pessoal.

---

## 1. Escopo e método

| | |
|---|---|
| Fonte | Caixa `ltog@cin.ufpe.br`, busca `achados-perdidos` |
| Período | 02/05/2025 a 13/10/2026 (17,5 meses) |
| Threads catalogadas | **441** (excluídas 3 que não eram da lista) |
| Como foi lido | Assunto, trecho inicial e metadados de todas as mensagens de cada thread. Texto integral em 3 threads que definem regra de processo. |
| Não foi lido | Anexos. Fotos e objetos que só aparecem na imagem ficaram marcados como `objeto_so_na_foto` |
| Arquivo de dados | [`threads.txt`](threads.txt): uma linha por thread, com tipo, objeto, local, bloco, custódia, desfecho e marcadores |

**Limites que importam:**
- A classificação é manual e feita a partir de trechos. Os 8 casos marcados `?` são justamente
  os que nem uma pessoa consegue decidir sem abrir a foto.
- A coluna "desfecho" registra só o que **aparece na lista**. Devolução combinada por resposta
  privada, WhatsApp ou corredor não aparece.
- A caixa só tem o que chegou até ela. Mensagens enviadas a outras listas sem cópia para
  `achados-perdidos@` não estão aqui.

---

## 2. Números

| Medida | Valor |
|---|---|
| Perdidos | 232 (53%) |
| Achados | 197 (45%) |
| Ambíguos (nem uma pessoa decide sem a foto) | 8 |
| Avisos de processo (descarte, registro) | 3 |
| Fora de tema | 1 |
| Threads com uma só mensagem | 379 (86%) |
| Threads de achado ou perdido **com desfecho registrado na lista** | **37 de 429 (8,6%)** |
| Threads enviadas por setor ou servidor (SecGrad, Gerinfra, recepção, professores) | 65 (15%) |
| Threads com cópia para outras listas (turmas, `alunos-grad-l`, `staff`) | 45 |

### Volume por mês

```
2025-05  45  ████████████████████████████████████████████▌
2025-06  42  ██████████████████████████████████████████
2025-07  28  ████████████████████████████
2025-08   6  ██████
2025-09  44  ████████████████████████████████████████████
2025-10  54  ██████████████████████████████████████████████████████
2025-11  32  ████████████████████████████████
2025-12  23  ███████████████████████
2026-01   1  █
2026-02   2  ██
2026-03  37  █████████████████████████████████████
2026-04  22  ██████████████████████
2026-05  21  █████████████████████
2026-06  18  ██████████████████
2026-07   2  ██
2026-08  16  ████████████████
2026-09  33  █████████████████████████████████
2026-10  15  ███████████████  (até 13/10)
```

A média é **~25 threads por mês**. Em semestre letivo, o volume fica entre 30 e 55 por mês. Nas
férias, cai para quase zero. A estimativa usada nas decisões de arquitetura era de **~10 itens por mês**.

### Objetos mais anunciados

| Objeto | Total | Achados | Perdidos |
|---|---|---|---|
| Garrafa | 83 | 38 | 41 |
| Fone (inteiro, um lado, só o case) | 73 | 29 | 42 |
| Carregador | 57 | 13 | 44 |
| Mouse | 30 | 9 | 20 |
| Crachá | 15 | 4 | 11 |
| Chave / chave de carro | 15 | 7 | 8 |
| Casaco | 13 | 8 | 5 |
| Guarda-chuva | 12 | 2 | 10 |
| Óculos, estojo, joia, celular, cartão, caderno | 9 a 11 cada | | |

Garrafa, fone e carregador somam **48%** do corpus. O vocabulário de objetos do extrator pode
começar por esses três.

Carregador é perdido 3,4 vezes mais do que é achado. A explicação provável é que quem acha um
carregador plugado no laboratório o deixa ali e não anuncia.

### Onde

| Bloco | Threads | |
|---|---|---|
| Vermelho (A) | 198 | 45% |
| Branco (E) | 119 | 27% |
| Não informado | 69 | 16% |
| Fora do CIn (estacionamento, parada de ônibus, outro centro, trajeto) | 32 | 7% |
| Mais de um bloco possível | 12 | 3% |
| B | 7 | 2% |

| Local | Threads |
|---|---|
| **Grad 5** | **59** |
| Grad 3 | 21 |
| Grad 2 / Grad 4 | 16 cada |
| Lab de hardware | 16 |
| Grad 1 | 15 |
| E112 | 12 |
| E132 | 11 |
| "No CIn" (sem local) | 19 |
| "Em um dos grads" | 9 |

O **Grad 5 sozinho tem 13% das threads**. Segundo o levantamento da SCRUM-64, é também a maior
sala (77 computadores).

### Com quem o objeto achado fica

| Custódia declarada no anúncio | Achados | Desfecho registrado |
|---|---|---|
| Não diz | 56 | 3 |
| Deixou no local | 33 | 7 |
| Ficou com quem achou | 33 | 1 |
| **SecGrad** (E124 / E123) | **30** | **7 "Item devolvido"** |
| Recepção ou portaria | 19 | 1 |
| Outro setor ou servidor (E126, Sec. Geral E423, Ascom, helpdesk, vigilância, técnico do lab) | 15 | 0 |
| Gerinfra (B021) | 7 | 1 |
| Ponto informal (escada do 2º andar do bloco E, E112) | 4 | 0 |

---

## 3. O que o corpus confirma

**Thread como unidade (decisão 4) funciona na maior parte dos casos.** 86% das threads têm uma
mensagem só. As respostas que existem quase sempre ficam dentro da thread.

**O vocabulário de situação é pequeno e repetitivo (decisão 5).** Apareceu de forma literal:

| Sinal | Exemplos (forma das frases) | Quem escreve |
|---|---|---|
| Reivindicação | "é meu", "era minha", "Opa, muito obrigado!! É meu!", "É o meu fone, onde posso pegar?", "Essa calça é minha, como eu pego" | Dono, respondendo ao achado |
| Reivindicação fraca | "Acredito que pode ser minha", "pode ser que talvez seja minha" | Dono, com dúvida |
| Encerramento pelo autor | "Encontraram :)", "Encontrado.", "Encontrei :)", "Achei, tava no DA", "Foi encontrado! Muito obrigado!", "Já encontrei e peguei na gerência" | Quem anunciou a perda |
| Encerramento pelo custodiante | "Item devolvido.", "O celular já foi devolvido ao proprietário.", "A chave já foi entregue.", "Chave entregue.", "Informamos que o vem já foi entregue" | SecGrad, Gerinfra |
| Encerramento por terceiro | "Pronto, foi resolvido, [fulana] achou o seu fone" | Outra pessoa da lista |

A frase **"Item devolvido."** da SecGrad é o sinal de encerramento mais confiável do corpus:
sempre o mesmo texto, sempre do mesmo remetente e sempre na mesma thread do anúncio.

**Reivindicar não é encerrar (decisões 5 e 14).** Há um caso explícito. Um professor anunciou
garrafas numa sala. Uma aluna respondeu "essa garrafa verde é minha" e, uma hora depois,
"fui lá e não encontrei". O professor confirmou que não havia garrafa verde. A thread tem
reivindicação e mesmo assim o objeto não voltou. Quatro dias depois, o professor escreveu:
"tudo continua lá, para pegar tem que dar um jeito de entrar na sala".

**A quarentena tem material de sobra (decisão 8).** São 8 threads em que nem uma pessoa decide
a direção sem a foto, 27 sem corpo (só assunto e imagem) e 17 em que o assunto contradiz o
corpo (ver §4.4).

**A preocupação com privacidade procede (decisão 10).** O corpus tem:
- 10 anúncios com **nome completo de terceiro** em documento achado (crachá, RG, VEM, cartão,
  carteira com identidade, caderno);
- 10 com **telefone** no corpo;
- 12 com **nome do dono gravado no objeto** e descrito no texto;
- 11 com objeto **sensível** (remédio, maquiagem, nécessaire, escova de dentes, cortador de unha);
- 1 com **placa de veículo**;
- 1 com o **e-mail de outra pessoa** escrito no corpo ("minha amiga perdeu, o e-mail dela é…").

---

## 4. O que o corpus muda ou refina

Os pontos abaixo esbarram em decisões de produto. Eles estão aqui como informação para o PO.
Nenhum foi implementado.

### 4.1 O volume é 2,5 vezes maior que o estimado, e sazonal

A estimativa de ~10 por mês (decisão 13) estava baixa. A média é 25, e o pico foi 54 em
out/2025. Isso não muda a arquitetura: o worker roda a cada 5 minutos e o custo continua
desprezível. Muda três coisas:
- **Catálogo:** em um semestre ele acumula ~150 itens, então paginação e filtro por local deixam
  de ser opcionais.
- **Recibos:** a decisão 9 prevê um recibo por thread, o que dá ~25 e-mails automáticos por mês.
- **Demonstração:** a banca vai ver o catálogo cheio ou vazio dependendo do mês em que
  acontecer. Julho e janeiro são quase vazios.

### 4.2 Existe custódia de fato, e ela é institucional

A premissa registrada até aqui é "não há custódia institucional; a cultura é deixar no lugar
e avisar". O corpus mostra um quadro mais dividido:

- A **SecGrad** recebe objetos, anuncia ("Para retirada na Secretaria de Graduação, sala E124")
  e fecha a thread com "Item devolvido". São 30 achados em 17 meses. É o único custodiante que
  registra desfecho com regularidade.
- A **Gerinfra (B021)** guarda celular, chave e dinheiro.
- **Outros setores** guardam quando quem acha trabalha neles: Gerência de Sistemas (E126),
  Secretaria-Geral (E423), Ascom, Cooperação, helpdesk, técnico do lab de hardware e vigilantes.
- **Portaria e recepção.** Há duas mensagens dizendo que não aceitam:
  - em out/2025, "corrigindo, não se pode deixar na portaria, acabei de descobrir";
  - em mar/2026, "a recepção não aceitou guardar" um casaco achado no estacionamento.

  Mesmo assim, 19 anúncios dizem "deixei na portaria/recepção", inclusive de servidores, e há um
  caso de dono que "achou na portaria do prédio".
- A **orientação escrita da Gerinfra** aparece numa assinatura de jul/2025: *"O CIn não possui
  achados e perdidos… Caso alguém ache algum produto, a pessoa deve ficar de posse do mesmo,
  aguardando que a pessoa que o perdeu entre em contato."* Ou seja, a regra oficial é **ficar
  com quem achou**, e não deixar no local.
- **Pontos informais:** "deixei no mesmo lugar onde sempre deixam as outras garrafas perdidas,
  no 2º andar do bloco E, nas escadas" e a sala E112, que acumula garrafas.

**Implicação:** o vocabulário de `localização` (hoje `no local` · `com quem achou` ·
`caixa do bloco A/E`) não tem valor para "com um setor". Mas é para lá que vão os objetos de
maior valor, como celular, documento e chave. **Decisão de produto.**

### 4.3 Já houve descarte com prazo, decidido pela instituição

Dois avisos:
- **ago/2025**, de servidor: "os itens permanecem nos corredores há bastante tempo… estarão
  disponíveis para retirada até terça-feira, dia 5. Após essa data, serão destinados para
  descarte ou doação." O prazo foi de 4 dias.
- **dez/2025**, da SecGrad: "o prazo de retirada encerra em 19/12/2025. Os itens não retirados
  serão descartados."

A invariante 7 (sem expiração por tempo) continua de pé: o sistema não inventa prazo. Mas o
corpus mostra que **a instituição descarta**, por iniciativa própria e sem periodicidade.
Depois de um descarte desses, os itens daquele lote continuam `aberto` no catálogo, e o
catálogo passa a mentir. Hoje não existe evento para "descartado pela instituição".
**Decisão de produto.**

### 4.4 O assunto mente: o classificador não pode confiar em [PERDIDO] e [ACHADO]

17 threads têm assunto de perda e corpo de achado. Exemplos parafraseados:
- assunto "[PERDIDO] Óculos escuros…", corpo "Encontrado no grad5";
- assunto "Bolsa perdida", corpo "Tem uma bolsa perdida no banheiro… o item se encontra no local";
- assunto "Celular PERDIDO", enviado pela Gerinfra, que estava com o celular;
- assunto "Sinalização de Perda", de servidor que achou dinheiro;
- assunto "Batom perdido no grad 4", de quem achou o batom.

O motivo: "perdido" descreve o **estado do objeto**, não a **ação de quem escreve**. O sinal
confiável está no verbo do corpo, na primeira pessoa:
- **perda:** "perdi", "esqueci", "deixei", "acredito ter esquecido";
- **achado:** "encontrei", "achei", "esqueceram", "alguém deixou", "foi encontrado".

**Implicação para a US-02:** as regras precisam dar mais peso ao corpo que ao assunto. Quando
os dois divergem e não há verbo claro no corpo, a mensagem vai para a quarentena. Isso já é
coerente com a decisão 8 e entra no corpus de teste (§6).

### 4.5 Só 8,6% das threads registram desfecho na lista

Das 429 threads de achado ou perdido, 37 têm reivindicação ou encerramento escrito na lista.
O resto se resolve por resposta privada, ao vivo, ou nunca se resolve.

**Implicação:**
- **Linha de base:** sem o sistema, o processo registra desfecho em **menos de 1 em cada 10
  casos**. É o número a comparar depois do recibo com token (decisão 9) e do lembrete
  (COULD, decisão 14).
- **Hipótese a verificar:** em 7 dos 30 achados da SecGrad o desfecho foi registrado. Isso
  sugere que um custodiante institucional fecha o ciclo muito mais do que pessoas isoladas.

### 4.6 Duplicatas fora da thread

- **12 anúncios repetidos pela mesma pessoa** em thread nova: o mesmo mouse duas vezes no
  mesmo dia, um crachá repetido 4 dias depois, "mouse e mousepad (continuam) perdidos".
- **10 casos de duplicata cruzada**, em que o mesmo objeto é anunciado por pessoas diferentes:
  - a perda e o achado do mesmo item em threads separadas;
  - o mesmo celular anunciado por duas pessoas no mesmo minuto;
  - o mesmo cartão anunciado por quem achou e pela SecGrad.

A decisão 4 aceitou isso de propósito: o sistema não tenta adivinhar que dois anúncios são o
mesmo objeto. O corpus confirma que o custo é real, mas pequeno: ~5% das threads.

### 4.7 Local é texto livre, às vezes impreciso, às vezes preciso demais

| Padrão | Quantas | Exemplo |
|---|---|---|
| Local vago | 38 | "no CIn", "em algum grad", "bloco vermelho ou branco" |
| Mais de um local | 25 | "Grad 5 ou lab de hardware", "E132, Grad 5 ou Grad 1" |
| Local preciso demais | 36 | "3ª fileira à esquerda, PC G5C08", "entre os computadores 21 e 22" |
| Local dado pela aula ou evento | 13 | "na aula de IP", "aula de Algoritmos", "sala do pitch na GGJ" |
| Fora do CIn | 32 | parada de ônibus, estacionamento, outro centro, ônibus, trajeto até o RU |

**Implicações:**
- **Extração (US-03):** "aula de Programação" não vira local. O campo fica vazio, o que é
  coerente com a decisão 8 (campo vazio é honesto).
- **Schema:** um único campo de local não representa "Grad 5 ou lab de hardware". Ou o campo
  vira lista, ou fica o primeiro local com o texto original visível. **Decisão de produto.**
- **Vocabulário:** precisa de um valor **"fora do CIn"**, porque 7% dos anúncios são de fora.
- **Dropdown (US-06):** as fileiras e os códigos de PC, como G5C08, mostram que quem anuncia
  pelo e-mail quer dar precisão. No site, a precisão deveria ir para um campo de texto livre e
  não para o dropdown.

### 4.8 Evidências para o levantamento de espaço físico (SCRUM-64)

- **Prédio vermelho = bloco A.** Há uma frase literal: "no Bloco A (prédio vermelho), muito
  possivelmente no Grad2".
- **Prédio branco = bloco E.** Há "sala E-132 do prédio branco" e "portaria do prédio branco".
- **Bloco B.** Aparecem a copa do bloco B, o banheiro feminino do bloco B, a B021 (Gerinfra)
  e a "B011 (Gerência de Sistemas) no prédio vermelho". **Pergunta aberta:** o prédio vermelho
  agrupa mais de uma letra (A e B)?
- **"Mezanino" existe nos dois prédios:** "mezanino do Bloco A" e "mezanino do bloco E
  (1º andar)". Sem o bloco, o nome é ambíguo.
- **Variações de grafia:** Grad 5, grad5, GRAD 05, grad05, Grad-5, G5, "grade 4", "lab Grad 05",
  "Laboratório de Graduação 01", "laboratório de informática 3", "Grad002". Confirma as quatro
  formas já previstas e acrescenta G5, "grade" e "laboratório de graduação NN".
- **Códigos de PC:** G5C08, G4C36, G3C32, G5C40, G5C44, G5C53. O padrão é Grad + nº + C + nº do
  computador.
- **Locais nomeados que ainda não estão no levantamento:** lab de hardware (C007?), lab da
  pós-graduação, anfiteatro (bloco A), auditório, DA, SandPit, copa e cantinas (A, B e E),
  refeitório do prédio vermelho, átrio e hall do bloco E, mesas externas de madeira,
  bicicletário, estacionamento (carros e motos), passarela em frente ao bloco A, helpdesk,
  APG, INES (3º andar do E), Lux AI, salas de reunião E102, E204, E402 e E403, e a Área II
  (salas 1, 5 e 10), que fica fora do prédio.

### 4.9 Ruído é raro, mas longo

São 7 threads com zoeira, que somam ~40 mensagens. Exemplos:
- uma nota de 2 reais achada que virou piada com 14 respostas, incluindo um "vocês vão ficar
  respondendo para todos igual criança?";
- uma mochila que virou "uma semana sem tomar água é tortura";
- "Papaloc Muncks";
- "Se não aparecer ninguém eu tô na fila";
- "como faço para não receber mais mensagens de achados e perdidos?".

Há ainda 1 thread totalmente fora de tema (convite para pesquisa).

**Implicação:** nenhuma dessas respostas pode mudar a situação do item. As palavras de
reivindicação ("é meu") não aparecem nelas, mas "Encontrei" aparece em contexto de piada. Para
o worker, a confiança precisa considerar quem escreve: o autor da thread ou o custodiante pesam
mais que um terceiro qualquer.

---

## 5. Implicações por componente

| Componente | O que o corpus pede | Depende do PO? |
|---|---|---|
| Classificação (US-02) | Verbo no corpo > assunto. Assunto e corpo divergentes sem verbo claro → quarentena. Thread sem corpo → quarentena, exceto se tiver foto e o objeto no assunto, que é achado (gabarito, caso 10). "Alguém viu…?" é perdido. | Decidido em 14/10 |
| Situação (worker) | Vocabulário da §3. "Item devolvido" da SecGrad como sinal forte. Respostas de terceiros não encerram sozinhas. | Peso por remetente: sim |
| Extração (US-03) | Objeto: garrafa, fone, carregador, mouse cobrem 55%. Item parcial ("lado esquerdo", "só a caixinha") é atributo, não outro objeto. | Não |
| Schema (F-02) | Local múltiplo. Valor "fora do CIn". Custódia em setor. Evento de descarte institucional. | **Sim** |
| Privacidade (US-05, US-09) | Nome de terceiro em documento, telefone, nome gravado no objeto e e-mail de terceiro no corpo são frequentes. O texto original visível (decisão 6) vai expor tudo isso. | **Sim** (ver §7) |
| Vocabulário de locais (SCRUM-64) | §4.8 | Levantamento em andamento |

---

## 6. Casos para o corpus de teste (SCRUM-74)

Casos difíceis para o corpus de teste. A coluna "proposta" foi a sugestão inicial. O PO fechou
o gabarito em 14/10/2026: 22 propostas aceitas, 3 decididas entre opções (casos 8, 19 e 26) e
3 mudadas (casos 10, 15 e 17). As regras que saíram do gabarito estão no backlog (US-02,
US-10, US-16 a US-18) e na invariante 2 do `AGENTS.md`.

| # | threadId | O que acontece (parafraseado) | Resposta esperada proposta | Gabarito do PO (14/10) |
|---|---|---|---|---|
| 1 | `199a9ead8208d070` | Assunto "[PERDIDO] Óculos", corpo "Encontrado no grad5" | Achado. O assunto não decide | Aceito |
| 2 | `1a11d14208192e67` | Assunto "Bolsa perdida", corpo diz que há uma bolsa no banheiro e que ela está no local | Achado, localização `no local` | Aceito |
| 3 | `19a07e69fb045ae6` | "[PERDIDO] Boné e garrafa", corpo "foi achado agora" | Achado, um item com dois objetos | Aceito |
| 4 | `1a110dd1782434ee` | Quem achou anuncia um batom como "perdido no grad 4". Uma pessoa diz "é meu". Um terceiro corrige: "Grad 3" | Achado → reivindicado. A correção do local é decisão em aberto | Aceito. O local fica "Grad 4" e a correção do terceiro vira evento (P5) |
| 5 | `1a0f91df0a9e6e4d` | Professor anuncia garrafas. Aluna diz "é minha", depois "fui lá e não encontrei" | Achado. A reivindicação não se confirma. Não avança para encerrado | Aceito |
| 6 | `19a83201eb17d35e` | Nota de 2 reais achada, 14 respostas de piada | Achado de valor trivial. Nenhuma resposta muda a situação | Aceito |
| 7 | `19a2611b68453a61` | Convite para pesquisa enviado para a lista | Não é achado nem perdido → quarentena | Aceito |
| 8 | `1a05e3826a6c31e8` | "Esqueci, já fui buscar e estou registrando porque a portaria pediu" | Não é anúncio. Nasce encerrado ou não vira item? **PO** | **Vira item já encerrado**, com a fonte "confirmação do autor" |
| 9 | `19b0e210c6ee699b` | SecGrad avisa que descarta o que não for retirado até uma data | Aviso de processo, não é item | Aceito. O descarte no catálogo virou COULD (US-16) |
| 10 | `19e833083f3a48fa` | Assunto "Garrafa no Grad 5", sem corpo, só foto | Direção desconhecida → quarentena | **Achado.** Sem corpo, com foto e objeto no assunto: quem perdeu não anuncia assim |
| 11 | `1999fe00ab68fae7` | Assunto "[PERDIDO]", corpo "Mouse deixado no Grad02" | Ambíguo → quarentena | Aceito: quarentena. A direção real é **perdido**, e o autor resolve em "Meus anúncios" |
| 12 | `19dc56af5351c01a` | "Levei para casa um casaco achando que era o meu" | Achado, `com quem achou` | Aceito |
| 13 | `19d97cca767f8d77` | "Perderam um crachá e um VEM no ônibus" | Achado, fora do CIn, documento de terceiro | Aceito |
| 14 | `1a048670b60f400a` | "Encontrei o crachá de [nome], vou deixar na portaria" | Achado, com nome de terceiro no texto → privacidade | Aceito. O texto original só aparece para quem entrou (P3) |
| 15 | `19cd8ee4645433b3` e `19cd8ed96f48d9e3` | O mesmo celular anunciado por duas pessoas no mesmo minuto | Dois itens. Duplicata aceita pela decisão 4 | **Dois itens por enquanto.** A COULD US-17 sinaliza a possível duplicata |
| 16 | `1997431ac10dcef4` e `1997771c7e257b74` | Perdeu fones. Um terceiro achou e deixou na SecGrad. A SecGrad anuncia em outra thread | Perdido → reivindicado na thread original. Achado separado | Aceito. O achado da SecGrad fica com a localização `com um setor · SecGrad` (P1) |
| 17 | `19a37f625dd8edd6` e `19a3a4e88cdb6d3b` | A mesma pessoa anuncia o mesmo mouse duas vezes | Dois itens. Duplicata | **Dois itens por enquanto.** A COULD US-17 sinaliza a possível duplicata |
| 18 | `19ce2ed8f4378fd3` | Perdeu a garrafa. A SecGrad diz que está lá. A SecGrad responde "Item devolvido" | Perdido → encerrado, fonte custodiante | Aceito: aberto → reivindicado ("está aqui") → encerrado |
| 19 | `19dd9b6a354dc246` | Achado. A dona diz que não encontrou. Um terceiro diz "resolvido, ela achou" | Encerrado por terceiro: confiança média | **Encerra direto, fonte "terceiro", confiança média.** A invariante 2 foi estendida |
| 20 | `1a08d70135f437bb` | Enviado para outra lista, depois encaminhado para esta. Depois: "Encontraram :)" | Perdido → encerrado. O encaminhamento não duplica | Aceito: encerrado direto, fonte "confirmação do autor" |
| 21 | `199e7b21ed281f95` | "Vou deixar na portaria", depois "corrigindo, não pode, fale comigo" | Achado. A localização muda por declaração explícita do autor | Aceito |
| 22 | `1a0d5a7f86366ff4` | "Perdi o lado esquerdo do AirPods" | Perdido, item parcial | Aceito |
| 23 | `1a0335d360fdb8ae` | "2 pendrives", três locais possíveis | Um item, local múltiplo | Aceito. Lista com três locais (P4) |
| 24 | `19d97fa6f853cbbc` | "Esqueci na aula de Programação" | Perdido, local vazio | Aceito. A COULD US-18 liga a aula à sala pela grade horária |
| 25 | `19995a5b465111bb` | Resposta: "como faço para não receber mais e-mails?" | Ruído. Não muda o estado | Aceito |
| 26 | `19b097e35b1544f6` | "Acredito que pode ser minha" | Reivindicação fraca. Avança ou não? **PO** | **Avança para reivindicado** |
| 27 | `196d0dd17b948374` | Só uma resposta ("errata: deixei na sala de aula"), sem a mensagem original | Thread incompleta → quarentena | Aceito |
| 28 | `19e3b47f06134368` | Mochila perdida, dois reforços e zoeira de colegas | Perdido. Continua aberto | Aceito |

---

## 7. Perguntas para o PO

Respondidas pelo PO em 14/10/2026. O registro no backlog e na arquitetura está no PR #2.

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Custódia em setor (§4.2) | `localização` ganha o valor **`com um setor`**, com o nome do setor em texto e sugestões (SecGrad E124, Gerinfra B021) |
| 2 | Descarte institucional (§4.3) | Vira **COULD (US-16)**. O PO vai levantar a regra de descarte com o CIn antes de escrever os critérios |
| 3 | Texto original e dado de terceiro (§3) | O texto original aparece **só para quem entrou** com a conta do CIn. Telefones e e-mails são mascarados para todos. A busca de quem não entrou não consulta o texto original |
| 4 | Local múltiplo (§4.7) | O `local` é uma **lista**, e o filtro por qualquer um deles encontra o item |
| 5 | Correção de local por mensagem seguinte | **Só o autor da thread corrige** o local. A correção de terceiro vira evento |
| 6 | Linha de base de desfecho (§4.5) | **Adotada: 8,6%**, registrada na US-14 |
| 7 | Volume real (§4.1) | Atualizado para **~25 por mês**, com pico de ~55 e quase zero nas férias |
