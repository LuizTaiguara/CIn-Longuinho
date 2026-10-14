# Backlog — Achados e Perdidos CIn-UFPE

**Disciplina:** IESI (CIN0139) · UFPE · 2026.2
**PO:** Luiz Taiguara
**Versão:** 01/10/2026 · revisado em 13/10/2026 (login com a conta do CIn, ADR-010)

---

## Como ler este documento

Cada história segue o formato **INVEST** e tem três blocos obrigatórios:

| Bloco | O que é |
|---|---|
| **História** | Quem, o quê, para quê |
| **Critérios de aceitação** | Condições verificáveis, em Gherkin (Dado/Quando/Então) |
| **Casos de falha** | O que acontece quando dá errado — e qual deve ser o comportamento |

A priorização usa **MoSCoW**: Must (sem isso não há produto), Should (o produto fica bom),
Could (se sobrar fôlego), Won't (explicitamente fora desta entrega).

**Princípio de arquitetura que atravessa todas as histórias:** o sistema informa, não arbitra,
e não depende de ninguém olhando. Ver `docs/ARQUITETURA.md` e `docs/ADR.md`.

**Estimativa:** escala de Fibonacci em pontos de história (1, 2, 3, 5, 8, 13).

---

# MUST

## US-01 · Ler mensagens da lista institucional

**Como** sistema,
**quero** ler periodicamente as mensagens que chegam ao endereço de achados e perdidos,
**para que** nenhum anúncio da comunidade fique fora do catálogo.

**Estimativa:** 5

### Critérios de aceitação

```gherkin
Dado que o worker está configurado com credenciais válidas
Quando ele executa um ciclo
Então ele deve buscar as mensagens recebidas desde o último ciclo
E registrar cada mensagem nova com seu identificador, remetente, data, assunto e corpo bruto
E não processar novamente nenhuma mensagem já registrada

Dado que uma mensagem já foi processada em um ciclo anterior
Quando o worker executa novamente
Então essa mensagem deve ser ignorada
E nenhum registro duplicado deve ser criado

Dado que o worker roda a cada 5 minutos
Quando não há mensagens novas
Então o ciclo deve encerrar sem erro e sem alterar o banco
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Credencial expirada ou revogada | Worker registra erro e encerra o ciclo. **Não** apaga estado nem marca mensagens como lidas. Próximo ciclo tenta de novo. |
| API do Gmail indisponível | Ciclo falha silenciosamente e tenta no próximo. Nenhum dado é perdido porque o estado vive no banco. |
| Mensagem sem corpo de texto (só anexo) | Registra a mensagem com corpo vazio e segue. Vai para quarentena na US-02. |
| Banco indisponível | Worker encerra sem consumir mensagens. Nada é marcado como processado. |
| Duas execuções simultâneas do worker | A segunda detecta execução em andamento e encerra. Sem processamento duplicado. |

---

## US-02 · Classificar mensagens e reter as duvidosas

**Como** sistema,
**quero** decidir se uma mensagem é de achados e perdidos e se trata de um achado ou de uma
perda,
**para que** o catálogo contenha apenas itens reais e na categoria correta.

**Estimativa:** 8

### Critérios de aceitação

```gherkin
Dado que uma mensagem foi registrada
Quando o classificador a avalia
Então ele deve responder se é achados e perdidos
E, em caso afirmativo, se é achado ou perda
E atribuir um grau de confiança a cada resposta

Dado que a mensagem não é de achados e perdidos
Quando a classificação termina
Então a mensagem vai para a quarentena
E não aparece no catálogo

Dado que a mensagem é de achados e perdidos
Mas o classificador não distingue se é achado ou perda
Quando a classificação termina
Então a mensagem vai para a quarentena
E não aparece no catálogo

Dado que a mensagem é de achados e perdidos e a direção é clara
Quando a classificação termina
Então o item é publicado no catálogo
Mesmo que os demais campos estejam vazios
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Mensagem claramente fora de contexto (ex.: discussão sobre comida na copa) | Quarentena. Não publica. |
| Texto ambíguo: "alguém viu um fone preto?" | Quarentena — pode ser perda ou achado, e publicar na categoria errada torna o item inencontrável. |
| Mensagem curta mas válida: "encontrei esse carregador no Grad 05" | **Publica.** Extração fraca não é motivo para reter. Campo vazio é honesto; campo errado não é. |
| Classificador indisponível ou com erro | Mensagem permanece não classificada e é reavaliada no próximo ciclo. Não publica por omissão. |

> **Nota:** a fila de quarentena é também o conjunto de teste do parser. Cada item retido é um
> caso não resolvido; revisá-la semanalmente indica quais palavras-chave faltam nas regras.

---

## US-03 · Extrair os dados do item

**Como** sistema,
**quero** identificar no texto da mensagem o objeto, o local, a data e o contato,
**para que** o catálogo seja pesquisável por esses campos.

**Estimativa:** 8

### Critérios de aceitação

```gherkin
Dado um item que passou pela classificação
Quando a extração é executada
Então os campos identificados devem ser preenchidos
E os campos não identificados devem permanecer vazios
E nenhum campo deve conter informação ausente do texto original

Dado que a mensagem menciona mais de um objeto
Quando a extração é executada
Então todos permanecem em um único item
E a descrição preserva a enumeração do texto original

Dado que a extração terminou
Quando o item é exibido para quem entrou com a conta do CIn
Então o texto original da mensagem deve estar visível junto ao item
E telefones e endereços de e-mail no texto aparecem mascarados
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Nenhum campo identificado | Item publica assim mesmo. Quem entrou vê o texto original e corrige mentalmente. Quem não entrou vê o item com campos vazios e o convite para entrar e ler o anúncio completo. |
| Campo extraído incorretamente (ex.: "Grad" como marca) | Publica. Quem entrou percebe o erro pelo texto original. Corrigível pelo autor (US-15). |
| Texto com erro de digitação ("harware", "fsbor") | Extração funciona com o que conseguir. Não falha o item. |
| Modelo de extração indisponível | Item publica só com classificação, sem campos extraídos. Reprocessável depois. |

---

## US-04 · Consultar o catálogo

**Como** pessoa que perdeu algo,
**quero** buscar no catálogo por descrição, local e período,
**para que** eu encontre meu objeto mesmo dias depois de tê-lo perdido.

**Estimativa:** 8

### Critérios de aceitação

```gherkin
Dado que existem itens publicados
Quando acesso o catálogo, mesmo sem entrar
Então vejo os itens ordenados do mais recente para o mais antigo
E cada item mostra descrição, local, data e situação

Dado que entrei com a conta do CIn
Quando abro um item
Então vejo também o texto original da mensagem, com telefones e e-mails mascarados

Dado que busco por um termo
Quando o termo aparece na descrição ou nos campos extraídos de um item
Então esse item aparece nos resultados
E a busca ignora diferenças de acento e de maiúsculas

Dado que não entrei com a conta do CIn
Quando busco por um termo que só aparece no texto original de um item
Então esse item não aparece nos resultados
E assim a busca não revela o que o texto original contém

Dado que filtro por local
Quando aplico o filtro
Então vejo apenas itens daquele local

Dado que um item está reivindicado mas não confirmado
Quando ele aparece no catálogo
Então mostra a situação e há quanto tempo está nela

Dado que nenhum item corresponde à busca
Quando os resultados são exibidos
Então vejo uma mensagem explicando que nada foi encontrado
E uma sugestão de buscar com menos termos
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Worker parado há dias | Catálogo continua funcionando com os itens que já tem. A dependência é só pelo banco. |
| Catálogo vazio (primeira execução) | Mensagem explicando que ainda não há itens, não uma tela em branco. |
| Busca com termo muito genérico ("preto") | Retorna muitos resultados, paginados. Não é erro. |
| Banco indisponível | Página de erro explicando que o catálogo está temporariamente fora, sem rastro de exceção. |

> **Pendente para a UI (Pedro e Rafael):** o catálogo separa achados e perdidos em abas
> distintas ou mostra tudo junto com filtro? Decisão de interface.

---

## US-05 · Não expor endereços de e-mail

**Como** pessoa que anunciou um objeto,
**quero** que meu endereço não apareça publicamente no catálogo,
**para que** eu não fique exposto a quem não tem relação com o anúncio.

**Estimativa:** 3

### Critérios de aceitação

```gherkin
Dado que um item foi publicado
Quando ele aparece no catálogo
Então o endereço de e-mail do autor não é exibido
E não está presente no código-fonte da página

Dado que quero falar com quem anunciou
Quando uso o botão de contato
Então minha mensagem é encaminhada sem que eu veja o endereço de destino

Dado que o texto original contém um telefone ou um endereço de e-mail
Quando o item é exibido
Então esses dados aparecem mascarados
E o mascaramento é feito no servidor, por regra determinística, antes de a API responder

Dado que não entrei com a conta do CIn
Quando abro um item
Então o texto original não é exibido
E não está presente na resposta da API nem no código-fonte da página
```

> **Decidido pelo PO em 14/10/2026:** como o catálogo é aberto na web e a lista é fechada ao
> CIn, o texto original, que traz nome de terceiro em documento, telefone e nome gravado no
> objeto, só aparece para quem entrou com a conta do CIn.

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Texto original contém o e-mail no corpo da mensagem | Aparece mascarado, inclusive para quem entrou. Decisão do PO em 14/10/2026. |
| Nome de terceiro no texto original (crachá, documento) | Visível só para quem entrou. A remoção segue possível pela US-09. |
| Telefone em formato que a regra não reconhece | Escapa do mascaramento. Cada formato novo encontrado vira caso de teste da regra. |
| Envio de contato falha | Mensagem de erro explicando que não foi possível enviar e sugerindo tentar mais tarde. |
| Uso do botão de contato para spam | Fora de escopo nesta entrega. Registrar como risco. |

---

## US-15 · Entrar com a conta do CIn e gerir meus anúncios

**Como** pessoa que anunciou um objeto,
**quero** entrar com a minha conta do CIn e ver os meus anúncios,
**para que** eu possa corrigi-los, encerrá-los ou removê-los sem depender de um link guardado
nem de outra pessoa.

**Estimativa:** 8
**Substitui:** US-08, que foi para WON'T em 13/10/2026. Decisão no ADR-010.

O token existia para evitar login. A justificativa era que login exige cadastro, senha,
recuperação e alguém para manter. Com o login Google restrito a `@cin.ufpe.br`, quem mantém
conta, senha e recuperação é o Google Workspace do CIn, e o R6 continua atendido. Em troca:
- acaba o risco de link encaminhado;
- ninguém perde acesso por apagar o e-mail;
- quem anunciou pela lista já é dono do item ao entrar.

### Critérios de aceitação

```gherkin
Dado que tenho uma conta @cin.ufpe.br
Quando clico em "Entrar com a conta do CIn"
Então sou autenticado pelo Google
E o sistema não pede nem guarda senha

Dado que tento entrar com uma conta de outro domínio
Quando o Google devolve a identidade
Então o acesso é recusado com uma mensagem explicando que só contas do CIn podem gerir anúncios
E o catálogo continua acessível para leitura

Dado que entrei com a minha conta
Quando acesso "Meus anúncios"
Então vejo todos os itens em que sou o autor
E isso inclui os que anunciei por e-mail na lista, antes de conhecer o site

Dado que estou em um anúncio meu
Quando corrijo a descrição, o local ou a localização atual
Então a alteração aparece no catálogo
E fica registrada como evento, sem apagar o valor anterior

Dado que estou em um anúncio meu, aberto ou reivindicado
Quando declaro que o objeto foi devolvido
Então a situação passa a "encerrado", mesmo que o anúncio ainda esteja "aberto"
E a fonte do encerramento fica registrada como "confirmação do autor"

Dado que estou em um anúncio meu
Quando peço a remoção
Então o item deixa de aparecer no catálogo
E o registro bruto permanece no banco

Dado que estou no anúncio de outra pessoa
Quando abro a página do item
Então não vejo as opções de corrigir, encerrar ou remover
E a API recusa essas operações com 403 mesmo que alguém tente chamá-las diretamente

Dado que um item foi publicado
Quando o worker termina de processá-lo
Então quem anunciou recebe um único aviso por conversa, por e-mail privado, com o link do item
E o aviso explica que basta entrar com a conta do CIn para corrigir ou encerrar
E o aviso não contém nenhuma credencial
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Login do Google indisponível | O catálogo segue funcionando para leitura. Só a gestão fica indisponível, com mensagem honesta. |
| Pessoa anunciou com e-mail de fora do CIn | Não consegue gerir o item. A remoção segue possível pelo canal de contato (US-09). |
| Ex-aluno sem conta ativa no CIn | Mesmo caso: canal de contato (US-09). |
| Sessão expira no meio da edição | Volta ao login e retorna ao mesmo item sem perder o que foi digitado. |
| Autor edita item já encerrado | Permitido. A situação não retrocede automaticamente. |
| Aviso enviado para a lista em vez de para o autor | **Defeito grave** de privacidade. Deve ser coberto por teste. |
| Recibo enviado várias vezes para a mesma conversa | **Defeito.** Deve haver verificação por conversa antes do envio. |

> **Decidido pelo PO em 14/10/2026:**
> 1. **O catálogo fica aberto para leitura, sem login.** O login é exigido só para anunciar e
>    para gerir os próprios anúncios. Quem não entrou vê só os campos extraídos. O texto
>    original aparece apenas para quem entrou com a conta do CIn (ver US-04 e US-05).
> 2. **O autor pode encerrar a partir de `aberto`**, pelo site ou por mensagem na thread. É a
>    exceção única à invariante 2: quem declara o próprio desfecho não precisa passar por
>    `reivindicado`. Mensagem de terceiro nunca pula etapa (US-10).

---

# SHOULD

## US-06 · Cadastrar um achado pelo site

**Como** pessoa que encontrou um objeto,
**quero** registrar o achado em poucos cliques, sem redigir e-mail,
**para que** avisar a comunidade custe menos esforço.

**Estimativa:** 5

### Critérios de aceitação

```gherkin
Dado que não entrei com a minha conta do CIn
Quando acesso o formulário de cadastro
Então sou levado a entrar com a conta do CIn (US-15)
E volto ao formulário depois de entrar

Dado que encontrei um objeto e entrei com a minha conta
Quando acesso o formulário de cadastro
Então escolho o local em uma lista predefinida dos espaços do CIn
E escrevo uma descrição breve
E informo onde deixei o objeto
E anexo uma foto, opcionalmente

Dado que preenchi os campos obrigatórios
Quando envio o formulário
Então o item é publicado imediatamente no catálogo
E não passa por classificação automática, pois os dados já vêm estruturados
E recebo a confirmação na tela com o link do item
E o autor do item é o e-mail da conta com que entrei

Dado que deixei um campo obrigatório vazio
Quando tento enviar
Então vejo qual campo falta, junto ao próprio campo
E o que já preenchi é preservado
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Local não está na lista predefinida | Deve haver opção "outro" com campo livre. A lista não pode bloquear o cadastro. |
| Foto muito grande ou formato não suportado | Mensagem explicando o limite. O resto do formulário é preservado. |
| Envio duplicado (clique duplo) | Apenas um item é criado. |
| Banco indisponível no momento do envio | Mensagem de erro pedindo para tentar novamente. Nada é perdido na tela. |

---

## US-07 · Publicar na lista o que foi cadastrado pelo site

**Como** comunidade do CIn,
**quero** receber por e-mail os achados cadastrados pelo site,
**para que** quem só usa e-mail continue sabendo de tudo.

**Estimativa:** 5
**Dependência externa:** permissão de postar no grupo `achados-perdidos@cin.ufpe.br`.

### Critérios de aceitação

```gherkin
Dado que um item foi cadastrado pelo site
Quando o envio é executado
Então uma mensagem é enviada à lista com assunto padronizado
E o remetente é a conta do sistema
E o campo Responder-Para é o endereço de quem cadastrou
E o corpo contém descrição, local, data e link do item no catálogo

Dado que alguém responde a essa mensagem
Quando a resposta é enviada
Então ela chega diretamente a quem cadastrou, sem passar pelo sistema

Dado que a permissão de postar ainda não foi concedida
Quando um item é cadastrado pelo site
Então ele é publicado no catálogo normalmente
E o envio fica pendente, sem bloquear o cadastro
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| **Permissão não concedida** | Sistema opera em modo somente leitura. O cadastro funciona, o catálogo funciona, só o envio não acontece. Nenhuma funcionalidade é bloqueada. |
| Envio falha por erro temporário | Reenviar no próximo ciclo, no máximo três tentativas. Depois, registrar como não enviado. |
| Mensagem enviada é relida pelo worker | Deve ser reconhecida como originada no sistema e **não** gerar item duplicado. |
| Conta do sistema sem permissão no momento do envio | Falha registrada, item permanece publicado no catálogo. |

> **Risco:** esta história depende de autorização de terceiros. Se a permissão não sair até a
> entrega, o sistema demonstra todas as demais funcionalidades. Ver decisão 3.

---

## US-09 · Pedir remoção de um item em que apareço

**Como** pessoa citada em um anúncio que não publiquei,
**quero** pedir que o item seja removido do catálogo,
**para que** meu nome não fique indexado publicamente.

**Estimativa:** 2

### Critérios de aceitação

```gherkin
Dado que apareço em um item sem tê-lo publicado
Quando acesso o canal de contato indicado no rodapé
Então consigo enviar um pedido de remoção identificando o item

Dado que um pedido de remoção é atendido
Quando a remoção é aplicada
Então o item deixa de aparecer no catálogo e nas buscas
E o registro bruto permanece no banco para auditoria

Dado que um item foi removido
Quando alguém acessa o link direto dele
Então vê uma mensagem informando que o item não está mais disponível
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| **Ninguém lê o canal de contato** | **Risco aceito e documentado.** Sem responsável designado após dezembro, o pedido fica sem destinatário. Ver decisão 15. |
| Pedido de remoção de item de terceiro, sem relação | Avaliação humana. Não há automação. |
| Remoção solicitada por engano | Reversível — o registro não foi apagado, apenas ocultado. |

---

## US-10 · Registrar a devolução automaticamente

**Como** comunidade,
**quero** que o sistema perceba quando alguém confirma ter recuperado seu objeto,
**para que** o catálogo não mostre como disponível algo que já foi devolvido.

**Estimativa:** 8

### Critérios de aceitação

```gherkin
Dado que uma resposta chega a uma conversa que já virou item
Quando o worker a processa
Então avalia se indica reivindicação ou devolução
E atualiza a situação do item conforme o caso

Dado que um item está aberto
Quando alguém responde indicando que o objeto é seu
Então a situação passa a reivindicado
E o momento da mudança é registrado

Dado que um item de perdido está aberto
Quando alguém que não é o autor responde dizendo que o objeto está com ele ("está aqui", "está comigo")
Então a situação passa a reivindicado
E o momento da mudança é registrado

Dado que um item está reivindicado
Quando há confirmação de que o objeto foi recuperado
Então a situação passa a encerrado
E a origem do encerramento é registrada

Dado que um item está aberto
Quando o próprio autor do anúncio responde declarando o desfecho ("Encontraram", "Achei já, obrigado")
Então a situação passa direto a encerrado
E a origem do encerramento é registrada como "confirmação do autor"

Dado que um item está aberto
Quando alguém que não é o autor responde declarando o desfecho
Então a situação não pula etapa
E o evento é registrado no histórico

Dado que um item já está encerrado
Quando chega nova resposta na conversa
Então a situação não é alterada
E o evento é registrado no histórico
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Detecção equivocada de devolução | **Falha mais cara do sistema** — mente para quem procura. Mitigação: só avança com alta confiança; autor corrige entrando com a conta do CIn (US-15). |
| Resposta ambígua ("achei!") | Não altera a situação. Registra o evento e mantém o estado anterior. |
| Reivindicação sem retirada posterior | Item permanece visível no catálogo mostrando há quanto tempo está reivindicado. Não reabre nem encerra sozinho. |
| Confirmação chega por fora da lista | Não é detectada. Encerramento depende do autor logado (US-15). Limitação conhecida. |

---

# COULD

## US-11 · Importar o histórico da lista

**Como** comunidade,
**quero** que o catálogo contenha também os anúncios anteriores à implantação,
**para que** o sistema nasça útil em vez de vazio.

**Estimativa:** 5
**Dependência externa:** arquivamento do grupo precisa estar ativo.

### Critérios de aceitação

```gherkin
Dado que existe histórico acessível
Quando a importação é executada
Então as mensagens anteriores passam pelo mesmo fluxo de classificação e extração
E itens antigos são marcados como importados
E a ordenação por data os coloca corretamente no catálogo
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Arquivamento desativado | Funcionalidade não é entregue. Sistema opera só com mensagens novas. |
| Mensagens antigas com formato diferente | Vão para quarentena como qualquer outra. |
| Importação parcial interrompida | Reexecutável sem duplicar — o controle de processados vale para o histórico também. |

---

## US-12 · Painel de curadoria

**Como** responsável pelo sistema,
**quero** revisar e corrigir itens em quarentena,
**para que** anúncios válidos que o sistema não entendeu possam ser publicados.

**Estimativa:** 8
**Condição:** só faz sentido se houver responsável designado. Se o processo for incorporado
institucionalmente, sobe para SHOULD.

### Critérios de aceitação

```gherkin
Dado que sou responsável e entrei com a minha conta do CIn
Quando acesso o painel
Então vejo a fila de quarentena com o motivo da retenção
E posso corrigir a classificação e publicar o item
E posso descartar o que não é achados e perdidos

Dado que publico um item que estava em quarentena
Quando a publicação ocorre
Então ele entra no catálogo normalmente
E gera o aviso de publicação como qualquer outro item
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Ninguém acessa o painel | Quarentena cresce sem efeito negativo no catálogo. Nada é publicado errado. |
| Quem é responsável | Definido por configuração, como uma lista de contas do CIn. Com o login individual (ADR-010), há auditoria por pessoa. |

---

## US-13 · Lembrete de confirmação

**Como** sistema,
**quero** perguntar se um item reivindicado foi efetivamente devolvido,
**para que** mais desfechos sejam registrados.

**Estimativa:** 3
**Por que permanece COULD:** não é falta de interesse — é decisão adiada por falta de dado.
Somar um segundo e-mail automático por ocorrência (além do aviso da US-15) exige antes medir
a taxa real de confirmação obtida pela US-10 e pelo encerramento do autor (US-15). Reavaliar com dado em mãos.

### Critérios de aceitação

```gherkin
Dado que um item está reivindicado há alguns dias sem encerramento
Quando a rotina de lembrete executa
Então uma mensagem é enviada a quem anunciou e a quem reivindicou
E contém um link direto para confirmar a devolução
E é enviada no máximo uma vez por item
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Percepção de spam | **Risco principal.** Soma-se ao aviso da US-15 — dois e-mails automáticos por ocorrência. Avaliar só depois de medir a taxa real de confirmação. |
| Lembrete enviado após devolução já ocorrida | Mensagem deve ser redigida como pergunta, nunca como cobrança. |

---

## US-14 · Painel de métricas do processo

**Como** setor que acompanha achados e perdidos no CIn,
**quero** ver quantos itens entraram e quantos foram devolvidos,
**para que** eu tenha pela primeira vez um registro do que hoje não é registrado.

**Estimativa:** 3
**Origem:** a secretaria de graduação comentou que hoje não há como registrar se os itens
retornam aos donos. É comentário espontâneo, não requisito formal — mas confirma, por um
segundo setor independente, que a lacuna incomoda quem opera.

### Critérios de aceitação

```gherkin
Dado que existem itens no catálogo
Quando acesso a página de métricas
Então vejo quantos itens foram publicados no período
E quantos estão abertos, reivindicados e encerrados
E o tempo mediano entre publicação e encerramento

Dado que os números são exibidos
Quando há desfechos não capturados
Então a página declara explicitamente que mede apenas desfechos registrados
E não apresenta os números como taxa de devolução real do CIn

Dado que não há itens suficientes no período
Quando acesso a página
Então vejo os números disponíveis sem extrapolação
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Interpretar o número como taxa real de devolução | **Risco principal.** A página deve declarar o escopo: mede o que foi declarado, não o que aconteceu. Um número honesto e parcial vale mais que um número completo e falso. |
| Volume baixo demais para conclusão | Exibe os valores absolutos. Não calcula percentual sobre base pequena. |
| Página acessada publicamente | Aceitável — são dados agregados, sem identificação de pessoas. |

> Responde ao comentário da secgrad por consulta ao banco, sem criar outro fluxo de e-mail —
> custa bem menos que a US-13 e ataca a mesma lacuna.

---

# WON'T — fora desta entrega

| Item | Motivo |
|---|---|
| **US-08 · Receber o recibo e poder corrigir o item** (link com token) | **Descontinuada em 13/10/2026, substituída pela US-15.** O token evitava login, mas o login com a conta Google do CIn não cria conta nem senha para o projeto manter. Ele também elimina o risco de link encaminhado e de acesso perdido. Ver ADR-010. O texto original da história está no histórico do git. |
| Notificação ativa a quem perdeu | Exige cadastro prévio da perda, o que compete com o e-mail. Classificado como *would* pelo PO. |
| Verificação automatizada de posse | Permanece presencial e social, como hoje. |
| Interpretação de imagens | Fotos são armazenadas e exibidas, não analisadas. |
| Tratamento de furto | Exige Boletim de Ocorrência para acesso às câmeras. O sistema pode orientar, não tratar. |
| Gamificação (CIn Longuinho) | Depende de haver desfecho registrado de forma confiável — o que a US-10 ainda vai estabelecer. |

---

# Dependências entre histórias

```
US-01 (ler)
  └─ US-02 (classificar)
       └─ US-03 (extrair)
            └─ US-04 (catálogo)  ← primeiro valor demonstrável
                 ├─ US-05 (privacidade)
                 ├─ US-15 (login e gestão pelo autor)
                 │    └─ US-09 (remoção)
                 └─ US-10 (devolução automática)

US-15 (login) ──→ US-06 (cadastro) ──→ US-07 (publicar na lista) [depende de autorização externa]

US-11, US-12, US-13 ─ independentes, COULD
```

**Caminho crítico:** US-01 → US-02 → US-03 → US-04. Com essas quatro, existe produto
demonstrável.

---

# Riscos registrados

| # | Risco | Natureza | Mitigação |
|---|---|---|---|
| R1 | Permissão de postar não ser concedida | organizacional | US-07 em SHOULD; sistema opera em modo somente leitura sem bloquear nada |
| R2 | Arquivamento do grupo estar desativado | externa | US-11 em COULD; catálogo nasce vazio e cresce |
| R3 | Detecção equivocada de devolução | técnica | Só avança com alta confiança; correção pelo autor logado (US-15) |
| R4 | Ausência de responsável após dezembro | organizacional | **Aceito pelo PO.** Sistema desenhado para operar sem supervisão |
| R5 | Pedido de remoção sem destinatário | legal | Decorre de R4. Mitigação sugerida: alias institucional |
| R6 | Volume insuficiente para demonstrar valor | produto | ~10 itens/mês; US-11 ajudaria se viável |
