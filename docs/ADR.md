# Registros de Decisão Arquitetural

**Sistema de Achados e Perdidos — CIn-UFPE**
Disciplina: Integração e Evolução de Sistemas de Informação (CIN0139) · 2026.2

---

## Sobre este documento

Cada registro abaixo documenta **uma decisão arquitetural**: a situação que a exigiu, as
alternativas consideradas, a opção escolhida e as consequências — inclusive as negativas.

O formato segue o **MADR** (*Markdown Any Decision Records*), que estende o modelo original de
Michael Nygard com duas seções que importam para este trabalho: *opções consideradas* e
*prós e contras de cada uma*. A escolha do formato é deliberada: registrar apenas a decisão
tomada produz um documento descritivo, enquanto registrar as alternativas descartadas e o
motivo produz um documento argumentativo — que é o que a modelagem arquitetural exige.

**Status possíveis:** `proposto` (em discussão) · `aceito` (acordado pela equipe) ·
`substituído por ADR-NNN` (quando uma decisão posterior o revoga).

| # | Decisão | Status |
|---|---|---|
| [ADR-001](#adr-001) | Estilo arquitetural orientado a dados compartilhados | aceito |
| [ADR-002](#adr-002) | Integração por consumo de canal de mensagens preexistente | aceito; assinatura **substituída por encaminhamento (ADR-011)** |
| [ADR-003](#adr-003) | Isolamento da fonte de dados atrás de interface | aceito |
| [ADR-004](#adr-004) | Retenção de mensagens não classificadas em quarentena | aceito |
| [ADR-005](#adr-005) | A conversa como unidade de registro | aceito |
| [ADR-006](#adr-006) | Correção por autosserviço, sem painel administrativo | aceito; credencial **substituída por ADR-010** |
| [ADR-007](#adr-007) | Resposta direcionada a quem anunciou, não ao sistema | **substituído por ADR-011** |
| [ADR-008](#adr-008) | Camada de acesso a dados exposta por interface de rede | aceito |
| [ADR-009](#adr-009) | Tecnologias de implementação | aceito |
| [ADR-010](#adr-010) | Autenticação do autor pela conta Google do CIn | aceito |
| [ADR-011](#adr-011) | Operar sem conta institucional: leitura por encaminhamento e anúncio pela conta de quem anuncia | aceito |

---
<a id="adr-001"></a>

# ADR-001 · Estilo arquitetural orientado a dados compartilhados

**Status:** aceito · **Data:** 01/10/2026 · **Decidido por:** equipe, com o PO

## Contexto e problema

O levantamento de campo documentado na Entrega 2 concluiu que o processo de achados e perdidos
do CIn **não possui responsável institucional**. Nem a portaria nem a Gerência de
Infraestrutura guardam objetos; o processo é comunitário e funciona por prática social.

Essa constatação tem consequência direta sobre a arquitetura. O sistema será entregue ao fim
de uma disciplina, e não há garantia de que alguém o mantenha depois. Qualquer componente que
dependa de supervisão humana contínua tende a degradar sem que ninguém perceba.

A pergunta arquitetural é, portanto: **como estruturar um sistema que continue correto quando
ninguém estiver olhando?**

## Critérios de decisão

- Falhas em um componente não podem comprometer os demais
- Cada parte deve poder ser desenvolvida, testada e implantada separadamente
- A ausência de supervisão não pode produzir estado incorreto
- A complexidade deve ser proporcional ao volume real (cerca de dez ocorrências por mês)

## Opções consideradas

1. Aplicação monolítica em camadas, com rotina agendada interna
2. **Arquitetura orientada a dados compartilhados**, com processos independentes
3. Microsserviços com comunicação por mensageria

## Decisão

Adotaremos uma **arquitetura orientada a dados compartilhados** (*shared-data style*). O
repositório de dados é o elemento arquitetural central, e os dois componentes do sistema —
o worker de ingestão e o site do catálogo — **não se comunicam entre si**: ambos conhecem
apenas o repositório.

O worker, internamente, organiza-se como **pipeline** (*pipes-and-filters*): ler → classificar
→ extrair → gravar, em que cada estágio transforma a informação e a repassa, e a retenção em
quarentena atua como filtro que interrompe o fluxo.

## Prós e contras das opções

**Monolítico em camadas**
Mais simples de implantar e de compreender, com uma única base de código em execução. Porém,
uma falha na rotina de ingestão derruba também a interface de consulta — e esta é a parte que
precisa permanecer disponível. Além disso, o modelo de extração ocupa memória significativa
que a camada de apresentação não teria motivo para carregar.

**Dados compartilhados** *(escolhida)*
Garante isolamento de falhas sem introduzir infraestrutura adicional, permite desenvolvimento
paralelo por subequipes e mantém um único ponto de verdade. Em contrapartida, exige disciplina
para que as regras de leitura não sejam reimplementadas de forma divergente em cada componente
— risco tratado na ADR-008.

**Microsserviços com mensageria**
Ofereceria desacoplamento ainda maior e escalabilidade horizontal. Para um volume de dez itens
mensais, com um único produtor e um único consumidor, acrescentaria componentes que podem
falhar sem resolver problema existente. A complexidade não encontra justificativa no domínio.

## Consequências

O site permanece operante ainda que o worker esteja parado — deixa apenas de receber itens
novos. O worker pode ser interrompido, corrigido e reiniciado sem afetar quem consulta o
catálogo. Cada componente é testável isoladamente.

Em contrapartida, assumimos o compromisso de manter as regras de acesso ao repositório em local
único e compartilhado, sob pena de divergência entre as visões de cada componente. Assumimos
também que a consistência entre eles é eventual: um item gravado pelo worker torna-se visível
no catálogo imediatamente, mas o worker não é notificado de alterações feitas pelo site.

**Observação metodológica:** esta arquitetura não decorre de preferência técnica, mas da
restrição organizacional identificada em campo. O encadeamento é explícito — ausência de
responsável → necessidade de sobreviver ao abandono → exigência de falhas independentes →
desacoplamento → repositório compartilhado como mecanismo mais simples disponível.

---
<a id="adr-002"></a>

# ADR-002 · Integração por consumo de canal de mensagens preexistente

**Status:** aceito · **Data:** 01/10/2026 · **Assinatura por conta de projeto substituída por**
[ADR-011](#adr-011), em 22/10/2026

## Contexto e problema

As ocorrências de achados e perdidos circulam hoje pelo endereço
`achados-perdidos@cin.ufpe.br`, que é um grupo do Google Workspace e redistribui as mensagens
às listas de turma do Centro. Trata-se de prática consolidada, com alto índice de satisfação
segundo a Gerência de Infraestrutura.

A restrição de projeto mais importante, estabelecida na Entrega 2, é que **nenhum participante
deve ser obrigado a alterar seu comportamento**. Quem hoje comunica um achado por e-mail deve
continuar podendo fazê-lo, sem tomar conhecimento da existência do sistema.

O problema arquitetural: como integrar-se a um sistema que não controlamos, não podemos
modificar e cujo comportamento não devemos perturbar?

## Critérios de decisão

- A prática atual não pode ser interrompida nem alterada
- O sistema não pode exigir modificação em componente de terceiros
- A integração deve tolerar indisponibilidade temporária de ambos os lados

## Opções consideradas

1. Substituir o fluxo de e-mail por formulário web, descontinuando a lista
2. **Inscrever um assinante automatizado no canal existente**
3. Solicitar que o CIn redirecione as mensagens para infraestrutura própria do projeto

## Decisão

O sistema será **mais um assinante do canal que já existe**. Uma conta de projeto é inscrita
como membro do grupo e passa a receber as mesmas mensagens que qualquer integrante da
comunidade; o worker lê dessa caixa.

Classificamos a integração em dois níveis, que convém distinguir: o **mecanismo** é de
invocação remota, pois o worker consome a interface programática do provedor de e-mail; o
**modelo** é de troca de mensagens, pois o correio eletrônico é, por natureza, comunicação
assíncrona com entrega desacoplada no tempo. O provedor desempenha o papel de intermediário de
mensagens.

```
achados-perdidos@cin.ufpe.br   ←  canal publish-subscribe preexistente
         │
         ├── assinantes humanos (comunidade, via listas de turma)
         └── assinante automatizado (worker)   ← acrescentado pelo projeto
```

## Prós e contras das opções

**Substituir o fluxo por formulário**
Produziria dados estruturados desde a origem, eliminando a necessidade de extração automática.
Contudo, competiria com uma prática estabelecida e bem avaliada — e, conforme analisado na
Entrega 2, uma solução que exige mudança de hábito tende a ser preterida em favor do hábito
existente. Rejeitada por contrariar a principal restrição de projeto.

**Assinante adicional** *(escolhida)*
Não requer alteração em nenhum componente existente, não perturba os demais assinantes e pode
ser revertida pela simples remoção da inscrição. O custo é depender de autorização
institucional e tolerar o formato livre das mensagens.

**Redirecionamento para infraestrutura própria**
Daria controle total sobre o recebimento, mas exigiria configuração administrativa no domínio
institucional, com risco de falha silenciosa caso o encaminhamento externo esteja restrito —
risco já identificado no documento de discovery.

## Consequências

O sistema integra-se sem alterar o comportamento de ninguém, e sua remoção é tão simples quanto
sua adição. Em contrapartida, ficamos sujeitos ao formato livre das mensagens, o que torna a
classificação automática necessária e imperfeita — consequência tratada na ADR-004.

Os seguintes padrões de integração descrevem decisões adotadas: *Polling Consumer* (o worker
busca periodicamente, pois não há notificação ativa), *Idempotent Receiver* (reprocessar uma
mensagem não duplica o item), *Message Filter* (a quarentena descarta o que não pertence ao
domínio), *Content Enricher* (a extração agrega estrutura ao texto bruto) e *Claim Check* (o
corpo original é preservado e referenciado, não relido da origem).

---
<a id="adr-003"></a>

# ADR-003 · Isolamento da fonte de dados atrás de interface

**Status:** aceito · **Data:** 01/10/2026

## Contexto e problema

A fonte de mensagens mudará ao menos uma vez durante o próprio projeto. O desenvolvimento
inicia lendo a caixa pessoal de um integrante da equipe, por não existir ainda conta
institucional; quando esta for criada e inscrita no grupo, a origem muda. São possíveis ainda
outras mudanças: alteração de provedor pelo Centro, reconfiguração do grupo, ou ingresso de
ocorrências por formulário web.

Simultaneamente, o desenvolvimento precisa avançar **antes** de a conta institucional existir,
e os testes não podem depender de credenciais nem de conexão com serviço externo.

## Critérios de decisão

- Trocar a origem dos dados não deve exigir alteração na lógica de processamento
- O pipeline deve ser testável sem credenciais e sem rede
- O conjunto de mensagens de teste deve ser reproduzível

## Opções consideradas

1. Acesso direto à interface do provedor a partir do worker
2. **Interface de fonte de mensagens com implementações intercambiáveis**
3. Fila de mensagens intermediária entre a origem e o worker

## Decisão

Tanto a leitura quanto o envio ficarão atrás de **abstrações com implementações
intercambiáveis**. O worker depende da abstração, não da origem concreta.

Para leitura: provedor de e-mail · arquivos locais · formulário web.
Para envio: lista institucional · não enviar · gravar em arquivo para inspeção.

A seleção da implementação ativa é feita por configuração, sem alteração de código.

## Prós e contras das opções

**Acesso direto**
Produz código mais curto e menos indireção. Entretanto, qualquer mudança de origem implicaria
reescrever o worker, e todo teste exigiria credencial válida e conexão ativa — inviabilizando o
desenvolvimento no período anterior à concessão da conta institucional.

**Interface com implementações** *(escolhida)*
Mantém a decisão registrada no documento de discovery, que já previa que "a leitura de e-mail
deve ficar atrás de uma interface com implementações trocáveis". Permite desenvolvimento e
teste imediatos, e torna a migração entre contas uma alteração de configuração. O custo é uma
camada adicional de indireção, modesta frente ao benefício.

**Fila intermediária**
Ofereceria desacoplamento ainda maior e tolerância a picos de carga. Para um produtor único e
volume mensal reduzido, introduz infraestrutura que pode falhar sem resolver problema
existente.

## Consequências

O pipeline completo é executável sem qualquer dependência de serviço externo, o que permite ao
subgrupo de back-end trabalhar imediatamente e torna a demonstração do sistema independente de
rede e credenciais.

A implementação que não envia mensagens permite que o sistema opere integralmente enquanto a
autorização para publicar na lista não é concedida: o cadastro funciona, o catálogo funciona, e
apenas a publicação permanece pendente — sem bloquear nenhuma funcionalidade.

Em contrapartida, assumimos que cada implementação precisa ser mantida em conformidade com a
abstração, e que a existência de múltiplas implementações exige disciplina para que o
comportamento permaneça equivalente entre elas.

---
<a id="adr-004"></a>

# ADR-004 · Retenção de mensagens não classificadas em quarentena

**Status:** aceito · **Data:** 01/10/2026

## Contexto e problema

As mensagens chegam em texto livre. A classificação automática — determinar se a mensagem trata
de achados e perdidos e, em caso afirmativo, se comunica um achado ou uma perda — está sujeita
a erro.

O corpus levantado contém casos ilustrativos: mensagens sobre assuntos não relacionados que
mencionam objetos; e mensagens genuinamente ambíguas, como o assunto *"[PERDIDO]"* com o corpo
*"Mouse deixado no Grad02"*, que pode comunicar tanto uma perda quanto um achado.

> **Revisão de 14/10/2026:** o exemplo original era *"alguém viu um fone preto perto do
> laboratório?"*. O PO decidiu que essa pergunta é uma perda, já que quem pergunta está
> procurando, e ela deixou de ser exemplo de ambiguidade.

Como o sistema não dispõe de curador — conforme ADR-001 — um item publicado incorretamente
permanecerá incorreto indefinidamente.

## Critérios de decisão

- Informação incorreta no catálogo é mais danosa que informação ausente
- Nenhuma mensagem pode ser perdida, ainda que não seja publicada
- O critério deve ser auditável e ajustável com base em dados reais

## Opções consideradas

1. Publicar todas as mensagens classificadas, aceitando o ruído
2. **Reter em quarentena as de classificação incerta**
3. Publicar com indicação visual de baixa confiança

## Decisão

Mensagens cuja classificação não atinja confiança suficiente **não são publicadas**: permanecem
em uma fila de quarentena, invisível ao público, com o conteúdo original preservado.

O critério de retenção considera **a classificação, não a extração**. Uma mensagem corretamente
classificada mas com poucos campos extraídos é publicada; campos vazios são honestos, campos
incorretos não são. O portão opera em duas perguntas: *trata de achados e perdidos?* e, em caso
afirmativo, *é possível determinar se é achado ou perda?* Resposta negativa a qualquer uma
resulta em quarentena.

## Prós e contras das opções

**Publicar tudo**
Maximiza a cobertura e evita que anúncios legítimos fiquem invisíveis. Contudo, um item
classificado na categoria errada torna-se inencontrável para quem o procura — e, sem curador,
permanece assim. O erro é silencioso, que é a característica que o torna caro.

**Quarentena** *(escolhida)*
Garante que o conteúdo publicado seja confiável e preserva integralmente o material retido para
reprocessamento posterior. O custo é a possibilidade de reter anúncios legítimos que o
classificador não compreendeu.

**Publicar com indicação de incerteza**
Preservaria a cobertura sinalizando a dúvida ao leitor. Pressupõe, entretanto, que o leitor
interprete corretamente o indicador — e não resolve o problema de o item estar na categoria
errada, pois quem procura na categoria oposta não o encontrará de qualquer modo.

## Consequências

O catálogo é menor e mais confiável do que seria com publicação irrestrita. Trata-se de um
compromisso deliberado: **em um sistema sem curador, um item incorreto custa mais que um item
ausente**, pois ninguém o corrigirá.

A fila de quarentena presta um segundo serviço, não previsto inicialmente: constitui o conjunto
de teste do classificador. Cada mensagem retida representa um caso não resolvido, e sua revisão
periódica indica quais termos e padrões faltam às regras. A fila é, simultaneamente, mecanismo
de proteção e instrumento de melhoria.

Assumimos que anúncios legítimos podem permanecer invisíveis até que o classificador seja
aprimorado ou que exista revisão manual — funcionalidade registrada no backlog com prioridade
condicionada à existência de um responsável.

---
<a id="adr-005"></a>

# ADR-005 · A conversa como unidade de registro

**Status:** aceito · **Data:** 01/10/2026

## Contexto e problema

Uma mesma ocorrência produz múltiplas mensagens. O corpus registra casos em que o autor
encaminha a própria mensagem para um segundo destinatário; em que reenvia o pedido dias depois
por falta de resposta; e em que terceiros respondem reivindicando o objeto ou confirmando a
recuperação.

Inversamente, uma única mensagem pode comunicar mais de um objeto — há registro de perda de
dois dispositivos de armazenamento anunciada em mensagem única.

A questão: o que constitui um item no catálogo?

## Critérios de decisão

- O catálogo não deve exibir a mesma ocorrência repetidamente
- Respostas devem ser associadas ao item que comentam
- A identificação não pode depender de julgamento sujeito a erro

## Opções consideradas

1. Cada mensagem gera um item
2. Cada objeto físico gera um item, com mensagens associadas
3. **Cada conversa gera um item**

## Decisão

A unidade de registro é a **conversa**, identificada pelo agrupamento que o próprio provedor de
e-mail fornece. Mensagens pertencentes à mesma conversa compõem um único item; as subsequentes
constituem eventos que podem alterar sua situação.

Múltiplos objetos comunicados em uma mesma mensagem permanecem em um único item, com a
descrição preservando a enumeração original.

## Prós e contras das opções

**Mensagem como unidade**
Simples e fiel à origem, sem necessidade de inferência. Produziria, contudo, itens duplicados
para reenvios e exibiria respostas de confirmação como se fossem novos anúncios.

**Objeto físico como unidade**
Seria conceitualmente correto e eliminaria toda duplicação. Exigiria, porém, determinar que
duas mensagens tratam do mesmo objeto — tarefa sujeita a erro cuja falha é grave: fundir em um
único registro objetos pertencentes a pessoas distintas. A alternativa de decisão manual
pressupõe um operador, inexistente por ADR-001.

**Conversa como unidade** *(escolhida)*
Aproveita agrupamento que a origem já fornece, sem exigir inferência. Resolve os casos de
encaminhamento, resposta e confirmação, que constituem a maioria. Não resolve reenvios em
conversas distintas, que permanecem como itens duplicados — defeito visível e de baixo custo.

## Consequências

O agrupamento vem pronto da origem, sem lógica adicional. Respostas de reivindicação e
confirmação associam-se naturalmente ao item correspondente, viabilizando a atualização
automática de situação.

Reenvios iniciados em conversa nova aparecerão como itens distintos. Trata-se de defeito
assumido conscientemente: é visível ao usuário, que compreende tratar-se da mesma ocorrência, e
seu custo é inferior ao risco de fusão indevida de registros.

---
<a id="adr-006"></a>

# ADR-006 · Correção por autosserviço, sem painel administrativo

**Status:** aceito · **Data:** 01/10/2026 · **Mecanismo de credencial substituído por
[ADR-010](#adr-010) em 13/10/2026.** Continua valendo: autosserviço do autor, ausência de
painel administrativo e canal humano para remoção a pedido de terceiros.

## Contexto e problema

O sistema cometerá erros: de extração, de classificação e de atualização de situação. Algum
mecanismo de correção é necessário.

A solução convencional — uma interface administrativa autenticada — pressupõe a existência de
alguém disposto a utilizá-la com regularidade. Conforme ADR-001, esse responsável não existe, e
o PO decidiu não designá-lo após o término da disciplina.

Há ainda uma obrigação distinta da correção: pessoas mencionadas em anúncios que não
publicaram, como ocorre quando um documento de identificação é encontrado e o nome do titular é
divulgado, precisam poder solicitar a remoção do registro.

## Critérios de decisão

- A correção não pode depender de supervisão contínua
- Quem tem contexto para corrigir deve ter meio de fazê-lo
- Pessoas citadas sem terem publicado precisam de um canal

## Opções consideradas

1. Interface administrativa autenticada
2. **Autosserviço por credencial de uso único enviada ao autor**
3. Correção comunitária, aberta a qualquer usuário
4. Ausência de mecanismo de correção

## Decisão

Quem publicou corrige o próprio item mediante **credencial de uso único**, enviada junto ao
comprovante de publicação. Não há autenticação, cadastro nem interface administrativa na
primeira versão.

A mesma credencial permite três ações: corrigir os dados, encerrar o item e solicitar sua
remoção. Para quem aparece em um anúncio sem tê-lo publicado, há um canal de contato que
conduz a avaliação humana.

Uma interface de curadoria sobre a fila de quarentena permanece registrada no backlog com
prioridade condicionada: caso o processo venha a ser incorporado institucionalmente, sua
prioridade se eleva.

## Prós e contras das opções

**Interface administrativa**
Permitiria correção abrangente, inclusive de itens de terceiros e da fila de quarentena. Exige,
contudo, autenticação, controle de acesso e — sobretudo — uma pessoa que se sinta responsável
por consultá-la. Construí-la equivaleria a edificar justamente o componente com maior
probabilidade de ser abandonado primeiro.

**Autosserviço por credencial** *(escolhida)*
Resolve o caso mais frequente com o menor custo, dispensando autenticação. A credencial no
vínculo enviado estabelece identidade de forma suficiente: quem o possui é quem recebeu a
mensagem, isto é, quem publicou. Não atende, porém, a correções em itens de terceiros.

**Correção comunitária**
Dispensaria qualquer autenticação e distribuiria o esforço. Constitui, entretanto, vetor
trivial de sabotagem: qualquer pessoa poderia encerrar o anúncio de outra, por malícia ou
engano, removendo-o das buscas. O custo do erro é elevado e assimétrico.

**Ausência de correção**
Seria coerente com a ausência de responsável, mas deixa sem resposta a solicitação de remoção
de dado pessoal, que constitui obrigação legal e não liberalidade.

## Consequências

A correção torna-se possível sem exigir infraestrutura de autenticação ou pessoa dedicada. O
mesmo mecanismo que permite corrigir permite encerrar — convertendo o instrumento de correção
em instrumento de captura de desfecho, o que atende simultaneamente a dois objetivos.

Erros em itens de terceiros e classificações incorretas permanecem sem correção automática. Isto
é aceitável para erros de extração, dado que o texto original acompanha cada item e permite ao
leitor identificar a discrepância.

Permanece em aberto, por decisão consciente do PO, quem atenderá às solicitações de remoção
após a dispersão da equipe. Registra-se como mitigação possível a criação de um endereço
institucional redirecionável, que sobreviveria às pessoas.

---
<a id="adr-007"></a>

# ADR-007 · Resposta direcionada a quem anunciou, não ao sistema

**Status:** substituído por [ADR-011](#adr-011) em 22/10/2026 · **Data:** 01/10/2026

## Contexto e problema

Quando o sistema publica na lista um item cadastrado pelo site, os destinatários podem
responder à mensagem. É necessário definir para onde essas respostas são encaminhadas.

A decisão afeta pessoas que não são usuárias do sistema: quem recebe a mensagem e responde pode
desconhecer inteiramente a existência do catálogo, e espera o comportamento habitual do correio
eletrônico.

## Critérios de decisão

- O comportamento de quem não é usuário do sistema não deve ser alterado
- Uma falha do sistema não pode interromper negociações em curso
- A exposição de endereços pessoais deve ser minimizada

## Opções consideradas

1. Respostas endereçadas ao sistema, que as processa e registra
2. **Respostas endereçadas a quem anunciou, por campo de resposta**
3. Envio em nome da própria pessoa, por delegação no domínio institucional

## Decisão

As mensagens publicadas pelo sistema terão como **remetente a conta do sistema** e como
**destinatário de resposta o endereço de quem anunciou**. As respostas chegam diretamente à
pessoa, sem intermediação.

## Prós e contras das opções

**Respostas ao sistema**
Proporcionaria registro completo de toda a negociação, com observabilidade superior. Altera,
contudo, o comportamento de todos os destinatários da lista — inclusive dos que nunca
utilizaram o sistema — e cria dependência crítica: uma interrupção no processamento prenderia
respostas em uma caixa não monitorada, interrompendo devoluções sem que ninguém o percebesse.

Acrescente-se que a observabilidade obtida seria parcial: o sistema registraria manifestações
de interesse, não a entrega efetiva do objeto, que permanece um ato físico fora de qualquer
canal eletrônico.

**Resposta direcionada ao autor** *(escolhida)*
Preserva integralmente o comportamento atual e mantém o sistema fora do caminho crítico da
devolução. A identificação do remetente como sistema tem efeito colateral favorável: divulga a
existência do catálogo a quem ainda o desconhece. Em contrapartida, a negociação não é
observável.

**Delegação de identidade**
Produziria mensagens indistinguíveis das enviadas manualmente. Exige, porém, delegação
administrativa no domínio institucional, procedimento sujeito a auditoria de segurança e
identificado como inviável já no documento de discovery. O ganho sobre a opção escolhida é
marginal.

## Consequências

Quem responde a um anúncio mantém a experiência de sempre, sem perceber mediação. O sistema
permanece fora do caminho crítico: sua indisponibilidade não impede nenhuma devolução.

A negociação não é registrada, e a captura de desfecho depende de confirmação explícita — pela
credencial do autor ou por detecção na conversa pública. Aceita-se que parte dos desfechos
permaneça invisível.

A exposição de endereços é adicionalmente mitigada pela decisão de não publicar o endereço de
quem anunciou na página do catálogo, substituindo-o por mecanismo de contato intermediado.

---
<a id="adr-008"></a>

# ADR-008 · Camada de acesso a dados exposta por interface de rede

**Status:** aceito · **Data:** 01/10/2026

## Contexto e problema

Decorre da ADR-001: se o repositório é o elemento arquitetural central e dois componentes o
acessam, é necessário definir **como** o acessam.

Há regras de leitura que precisam valer uniformemente: itens removidos a pedido não podem
aparecer; itens retidos em quarentena não podem aparecer; itens encerrados aparecem com
indicação de situação. Caso cada componente implemente essas regras independentemente, elas
divergirão — e a divergência expõe dados que não deveriam ser exibidos.

## Critérios de decisão

- As regras de visibilidade devem existir em local único
- A solução deve ser proporcional ao número de clientes do repositório
- A estrutura não deve antecipar necessidades que podem não se concretizar

## Opções consideradas

1. Cada componente constrói suas próprias consultas
2. **Camada de acesso a dados compartilhada entre os componentes**
3. Interface programática interna, consumida pelo site por protocolo de rede

## Decisão

As consultas ao repositório residirão em uma **camada de acesso a dados**, que concentra as
regras de visibilidade e expõe operações nomeadas — *itens publicados*, *itens por local*,
*fila de quarentena* — em vez de permitir que cada componente construa consultas diretamente.

A equipe decidiu implementar a interface de usuário em tecnologia distinta da do worker. Como
componentes em linguagens diferentes não compartilham módulos, **a camada é exposta por
interface programática de rede**, consumida pelo site. O worker, escrito na mesma linguagem da
camada, a importa diretamente.

Registra-se que esta é a condicionante prevista quando a decisão foi formulada: **a adoção da
interface de rede é consequência da escolha de implementação, não um fim em si.** Caso o
sistema fosse implementado integralmente em uma única linguagem, a importação direta seria
suficiente e preferível.

## Prós e contras das opções

**Consultas independentes**
Reduz indireção e mantém cada componente autocontido. Contudo, replica as regras de
visibilidade, e a replicação diverge com o tempo. O modo de falha é particularmente
indesejável: a omissão de um filtro expõe publicamente dado que deveria estar oculto.

**Camada compartilhada** *(escolhida)*
Mantém as regras em local único, alinhada ao princípio da ADR-001 de que o repositório é
elemento central e, portanto, suas regras de acesso também devem ser centralizadas. Introduz
acoplamento entre os componentes pela camada comum — acoplamento aceitável, pois é
precisamente o que garante a consistência desejada.

**Interface programática de rede** *(adotada por decorrência)*
Torna-se necessária quando os componentes são implementados em linguagens distintas, como é o
caso. Acrescenta serialização, latência e uma superfície adicional de falha, mas estabelece
contrato explícito entre interface de usuário e repositório — o que, em uma equipe com
subgrupos distintos atuando em cada lado, facilita o trabalho paralelo.

## Consequências

As regras de visibilidade existem em um único ponto, e sua alteração propaga-se a todos os
consumidores simultaneamente. Testá-las uma vez basta.

A interface de rede introduz um contrato explícito entre o site e o repositório, o que permite
que os subgrupos de interface e de processamento trabalhem em paralelo a partir da definição
das operações. Em contrapartida, acrescenta um ponto de falha: a indisponibilidade da camada
torna o catálogo inacessível, ainda que os dados permaneçam íntegros.

Observe-se que este acoplamento é de natureza distinta do acoplamento entre componentes
rejeitado na ADR-001. Ali, tratava-se de dependência de execução entre worker e site, cuja
falha se propagaria de um para o outro. Aqui, a dependência é do site em relação ao
repositório, que é precisamente a relação que o estilo arquitetural adotado prevê — o site
continua sem conhecer o worker.

---
<a id="adr-009"></a>

# ADR-009 · Tecnologias de implementação

**Status:** aceito · **Data:** 01/10/2026 · **Decidido por:** equipe de desenvolvimento

## Contexto e problema

A equipe é composta por sete integrantes do terceiro período, com subgrupos distintos para
processamento, interface e pesquisa. O componente de extração de informação depende de
biblioteca de reconhecimento de entidades disponível em Python, o que condiciona a linguagem
do worker.

Restava decidir a linguagem da interface de usuário e o sistema de banco de dados — decisões
que, embora frequentemente tratadas como implementação, afetam a estrutura do sistema e
condicionam a ADR-008.

## Critérios de decisão

- Aproveitar competências já existentes na equipe, dado o prazo da disciplina
- Permitir trabalho paralelo entre subgrupos
- Suportar dois processos escrevendo simultaneamente no repositório
- Oferecer busca textual adequada ao português

## Opções consideradas

**Para a interface:** implementação em Python, compartilhando linguagem com o worker · **
implementação em JavaScript**, com interface de rede entre as partes.

**Para o repositório:** banco relacional embarcado em arquivo · **banco relacional em
servidor**.

## Decisão

A interface de usuário será implementada em **JavaScript**, e o worker em **Python**. O
repositório será um **banco relacional em servidor**, do tipo que suporta acesso concorrente.

## Prós e contras das opções

**Interface em Python**
Permitiria uma única linguagem em todo o sistema, com a camada de acesso a dados importada
diretamente e o esquema definido uma só vez. Em contrapartida, exigiria que o subgrupo de
interface aprendesse tecnologia nova durante o prazo da disciplina, em vez de produzir com o
que já domina.

**Interface em JavaScript** *(escolhida)*
Aproveita a experiência prévia do subgrupo responsável pela interface e permite que as duas
frentes avancem em paralelo a partir do contrato de rede. Introduz, porém, uma fronteira de
linguagem no interior da equipe: integrantes de um subgrupo não conseguem auxiliar diretamente
no trabalho do outro, e a definição das estruturas de dados passa a existir em dois lugares,
com risco de divergência.

**Banco embarcado em arquivo**
Dispensaria configuração e instalação, reduzindo o atrito inicial para uma equipe numerosa e
pouco experiente. Entretanto, apresenta contenção quando dois processos escrevem
simultaneamente — exatamente o cenário do sistema — e oferece busca textual limitada para o
português, que é funcionalidade central do catálogo.

**Banco em servidor** *(escolhido)*
Suporta escrita concorrente sem contenção e dispõe de busca textual com tratamento de acentuação
e flexão em português. Exige configuração inicial e credenciais, custo pontual frente ao
benefício permanente.

## Consequências

A fronteira de linguagem entre os subgrupos exige que o contrato da interface de rede seja
definido cedo, pois ambos os lados dependem dele para avançar. Esta é a principal implicação
de cronograma decorrente desta decisão.

A definição das estruturas de dados passa a existir em duas linguagens. Assume-se o risco de
divergência, mitigado pela centralização das regras de visibilidade na camada de acesso, que
permanece do lado do servidor.

A adoção de banco em servidor viabiliza a busca textual adequada ao português sem
desenvolvimento adicional, e elimina a contenção de escrita que a arquitetura de dois processos
tornaria recorrente.

---
<a id="adr-010"></a>

# ADR-010 · Autenticação do autor pela conta Google do CIn

**Status:** aceito · **Data:** 13/10/2026 · **Substitui** o mecanismo de credencial do
[ADR-006](#adr-006)

## Contexto e problema

O ADR-006 resolveu a correção por autosserviço com uma **credencial de uso único** enviada no
recibo: um link com token. O motivo para evitar login era que ele exigiria cadastro, senha,
recuperação de acesso e alguém para manter as contas, o que o R6 proíbe.

Esse motivo vale para um sistema de contas próprio. Não vale para a conta institucional que
toda a comunidade já tem. O domínio `@cin.ufpe.br` é Google Workspace: quem mantém conta, senha
e recuperação é o Google e a administração do CIn, não o projeto.

O token tem ainda custos próprios:
- **Encaminhar o recibo é entregar o controle do item.** Um print ou um encaminhamento basta.
- **Quem apaga o e-mail perde o acesso** e não tem como recuperar.
- **O link precisa ser protegido** em logs, páginas e respostas da API.

## Critérios de decisão

- Não criar papel humano novo nem gestão de contas (R6)
- Só o autor corrige, encerra e remove o próprio item
- Não expor o e-mail de ninguém (invariante 1)
- Funcionar também para quem anunciou pela lista, sem nunca ter visitado o site

## Opções consideradas

1. Link com token no recibo (ADR-006)
2. **Login Google restrito ao domínio `@cin.ufpe.br`**
3. Contas próprias com senha
4. Link mágico por e-mail a cada acesso

## Decisão

O autor **entra com a conta Google do CIn**. O servidor aceita apenas identidades verificadas
pelo Google cujo domínio seja `cin.ufpe.br`, e compara o e-mail da sessão com o e-mail de autor
do item. Esse e-mail vem do remetente da thread ou da conta que cadastrou pelo site. Se forem
iguais, a pessoa pode corrigir, encerrar e remover. Se não forem, a resposta é 403.

O recibo continua existindo como **aviso de publicação e canal de divulgação** (decisão 9),
com o link do item e a instrução para entrar com a conta do CIn. Ele não carrega credencial.

O sistema não tem tabela de usuários nem de senhas. A identidade é obtida do Google a cada
login. O e-mail do autor fica guardado no banco apenas para a comparação e **nunca sai em
resposta da API**.

**O catálogo continua aberto para leitura, sem login** (decisão do PO em 14/10/2026). O
login é exigido para anunciar e para gerir os próprios anúncios. A sessão também passa a
liberar o **texto original** de cada item, que quem não entrou não vê, porque ele traz nomes de
terceiros e dados de contato que hoje só circulam dentro do CIn.

## Prós e contras das opções

**Link com token**
Não exige nenhuma integração. Por outro lado, transfere o controle a quem receber o e-mail
encaminhado e se perde com o e-mail apagado. Também exige proteger o link em todos os pontos
por onde ele passa.

**Login Google restrito ao domínio** *(escolhida)*
Não cria conta, senha nem recuperação para o projeto manter. Elimina o risco de encaminhamento.
Torna o autor de um anúncio feito pela lista dono do item sem nenhum passo extra. Abre
espaço para uma tela de "meus anúncios".

Em contrapartida:
- **Exige um app OAuth no Google Cloud.** Com o projeto do CIn (pedido 5 à Gerinfra), o app
  fica do tipo "Interno". Sem ele, serve um app "Externo" com escopo só de identidade e o
  domínio filtrado no servidor. O pedido foi negado em 22/10/2026, e vale o app "Externo"
  (ADR-011).
- **Exige gestão de sessão no site.**
- **Exclui quem anuncia com e-mail de fora do CIn**, que no corpus é 1 caso em 441, e quem
  perdeu a conta ao se formar. Para esses resta o canal de contato da US-09.

**Contas próprias com senha**
Recria exatamente o que o R6 proíbe: cadastro, senha, recuperação e alguém para atender.

**Link mágico a cada acesso**
Evita guardar credencial permanente, mas o sistema passa a mandar e-mail a cada acesso e
continua vulnerável a encaminhamento. Não oferece nada que o login do Google não ofereça
melhor.

## Consequências

- A **US-08** (recibo com token) vai para WON'T e é substituída pela **US-15** (entrar com a
  conta do CIn e gerir meus anúncios), classificada como MUST.
- O **cadastro pelo site (US-06)** passa a exigir login. Dele vem o autor do item. O
  `Reply-To` da US-07 deixou de existir com o ADR-011.
- O **contrato da API** passa a declarar sessão em `POST /itens`, `PATCH /itens/{id}` e
  `POST /itens/{id}/encerrar`, com 401 sem sessão e 403 para quem não é o autor, e ganha
  `GET /eu/itens`.
- O **client secret** do OAuth entra na configuração por variável de ambiente (invariante 9).
- O sistema passa a depender do login do Google para a gestão de itens. Já dependia do Google
  Workspace para ler a lista. Se o login estiver indisponível, **o catálogo continua
  funcionando para leitura**, e só a gestão fica parada.
- Quem aparece num anúncio sem tê-lo publicado continua sem poder removê-lo sozinho, mesmo
  logado, porque não é o autor. O canal humano da US-09 permanece.
- **O autor pode encerrar a partir de "aberto"** (decisão do PO em 14/10/2026), pelo site ou
  por mensagem na thread. No mesmo dia, o gabarito do corpus estendeu essa exceção à
  invariante 2 para a declaração de terceiro na thread, registrada com a fonte "terceiro" e
  confiança média (US-10).
- O texto original passa a sair da API só para sessão do CIn, com telefones e e-mails
  mascarados (US-04 e US-05).

---
<a id="adr-011"></a>

# ADR-011 · Operar sem conta institucional: leitura por encaminhamento e anúncio pela conta de quem anuncia

**Status:** aceito · **Data:** 22/10/2026 · **Decidido por:** PO · **Substitui** o
[ADR-007](#adr-007) e o mecanismo de assinatura do [ADR-002](#adr-002)

## Contexto e problema

Em 13/10/2026 o projeto pediu formalmente à Gerinfra conta institucional, inscrição no grupo,
permissão de postar, preservação do `Reply-To`, API do Gmail com projeto no Google Cloud do
CIn, alias de contato e Takeout do histórico. Em 22/10/2026 a Gerência de Sistemas negou: "a
política atual não permite a concessão de permissões parciais para [...] criação/gerenciamento
de contas, autenticações personalizadas e liberações para uso de APIs". O PO decidiu não
insistir na conta institucional.

Quatro coisas dependiam dela:
- **ler a lista**, por uma conta de projeto inscrita no grupo (ADR-002);
- **publicar na lista** o que foi cadastrado no site, com remetente do sistema e `Reply-To` da
  pessoa (ADR-007, US-07);
- **enviar o aviso privado** ao autor depois da publicação (US-15);
- **o alias de contato** para pedidos de remoção (US-09).

## Critérios de decisão

- Não depender de autorização institucional
- Não mudar o comportamento de quem só usa e-mail (ADR-002)
- As respostas continuam indo direto a quem anunciou (ADR-007)
- Retomar o sistema depois de um abandono deve custar pouco (R6)

## Opções consideradas

Para a leitura:
1. O worker lê direto a caixa `@cin.ufpe.br` de um integrante, pela API do Gmail
2. **Um filtro na caixa `@cin.ufpe.br` de um integrante encaminha a lista para uma conta Gmail
   do projeto**
3. Só o corpus local

Para o anúncio feito no site:
4. A conta Gmail do projeto posta na lista, com `Reply-To` da pessoa
5. **O site abre um e-mail pronto, que a pessoa envia da própria conta**
6. O cadastro pelo site não vai para a lista

## Decisão

**Leitura.** Um filtro na caixa de um integrante inscrito na lista encaminha as mensagens de
`achados-perdidos@cin.ufpe.br` para uma conta Gmail do projeto, fora do domínio do CIn. O worker
lê essa conta. Para o pipeline, nada muda: é outra implementação da interface de leitura
(ADR-003).

**Anúncio feito no site.** O sistema não posta na lista. Depois do cadastro, o site abre um
e-mail pronto, saindo da conta da pessoa, com o link e um código do item. Quando o worker lê
esse e-mail na lista, reconhece o código e liga a thread ao item já publicado, sem classificar
nem criar item novo.

**Envio privado e contato.** A conta Gmail do projeto envia o aviso de publicação ao autor
(US-15) e recebe os pedidos de remoção num endereço `+remocao` (US-09).

**Login.** O ADR-010 continua valendo, com o app OAuth "Externo" num projeto Google Cloud da
equipe, só com escopos de identidade e o domínio filtrado no servidor.

**Plano B.** Se o CIn bloquear o encaminhamento para fora, a demonstração roda com o corpus
local, e a questão volta ao PO com o resultado do teste.

**Teste (22/10/2026):** o encaminhamento da caixa `@cin.ufpe.br` para a conta Gmail do projeto
funciona.

**Cabeçalhos (28/10/2026), conferidos no primeiro anúncio real encaminhado:**
- `From` e `Message-ID` chegam preservados. A assinatura DKIM de `cin.ufpe.br` passa, então o
  remetente é confiável.
- **`List-ID` não identifica a lista.** A mensagem chega à caixa de origem por listas aninhadas
  (`achados-perdidos` → lista de alunos → lista da turma), e o `List-ID` é o da última, a da
  turma. Quem prova a passagem pela lista é o cabeçalho `X-BeenThere`, que aparece uma vez por
  lista e inclui `achados-perdidos@cin.ufpe.br`. O worker reconhece a lista por ele.
- Falta conferir `References` e `In-Reply-To` numa resposta a um anúncio.
- O encaminhamento depende de o integrante seguir inscrito na cadeia de listas (risco R7).

## Prós e contras das opções

**Ler direto a caixa do integrante**
Dispensa conta nova. Por outro lado, é justamente o uso de API que a Gerência de Sistemas disse
não liberar, e o administrador do domínio pode bloquear o app a qualquer momento. A credencial
também seria a de uma pessoa, com acesso à caixa inteira dela.

**Encaminhamento para a conta do projeto** *(escolhida)*
A conta do projeto fica fora do controle do administrador do CIn. A caixa do integrante só
precisa de um filtro, sem credencial compartilhada. Retomar o sistema é refazer o filtro em
qualquer caixa inscrita na lista.

Em contrapartida:
- **Depende da caixa de uma pessoa**, e isso fere o R6 em parte.
- **A falha é silenciosa.** Se o filtro sumir, o worker não distingue isso de uma lista quieta.
  É o risco que o ADR-002 apontou para o redirecionamento, agora num nível que qualquer membro
  da lista desfaz e refaz.

**Só o corpus local**
Não tem risco externo nenhum, mas o catálogo nunca recebe um anúncio real. Fica como plano B.

**A conta do projeto posta na lista**
Mantém a US-07 como estava. Porém, um remetente de fora do domínio tende a ser barrado ou
moderado pelo grupo, e nada garante que o `Reply-To` seja respeitado.

**E-mail pronto enviado pela pessoa** *(escolhida)*
Não exige permissão nenhuma. O remetente é a pessoa, e as respostas chegam a ela sem
`Reply-To`. Para a lista, o e-mail é igual a um anúncio feito à mão, que era o que a delegação
de identidade do ADR-007 buscava, agora sem delegação.

Em contrapartida, depende de a pessoa clicar em enviar, e ela pode editar o código. O item pode
ficar só no catálogo, e por isso "Meus anúncios" mostra o que ainda não foi para a lista.

**Não publicar na lista**
Quebra a paridade: quem só usa e-mail deixa de ver os anúncios feitos pelo site.

## Consequências

- **US-07:** muda de formato e é entregue junto com a US-06. O risco R1 deixa de existir.
- **ADR-007:** fica substituído. Não há conta do sistema enviando para a lista, e sai o aviso
  discreto sobre o `Reply-To` da US-06.
- **Worker:** ganha uma regra. Uma mensagem com o código de um item cadastrado pelo site é
  ligada a esse item, sem passar pela classificação.
- **US-11:** vai para WON'T. O Takeout do grupo foi negado. Importar da caixa pessoal publicaria
  nomes de terceiros de anos atrás e, sem expiração por tempo (invariante 7), deixaria os
  anúncios antigos `aberto` para sempre.
- **US-09:** o alias foi negado. O contato passa a ser o endereço `+remocao` da conta do
  projeto, e a limitação de ARQUITETURA §3.7 continua.
- **R6:** a conta do projeto e o filtro passam a ter dono. Um doc de passagem, sem credenciais,
  explica como transferir a conta e como refazer o filtro. Se ninguém assumir, o catálogo para
  de receber anúncios, e o site segue no ar com o que já tem.
- **Credenciais:** as da conta do projeto entram só por variável de ambiente (invariante 9).
- **ADR-003:** absorve a mudança. Trocar a origem é configurar outra implementação de leitura.

---

## Referências

- NYGARD, M. *Documenting Architecture Decisions*. 2011.
  https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- MADR — *Markdown Any Decision Records*. https://adr.github.io/madr/
- HOHPE, G.; WOOLF, B. *Enterprise Integration Patterns*. Addison-Wesley, 2003.
