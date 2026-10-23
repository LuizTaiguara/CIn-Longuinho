# Backlog — Achados e Perdidos CIn-UFPE

**Disciplina:** IESI (CIN0139) · UFPE · 2026.2
**PO:** Luiz Taiguara
**Versão:** 01/10/2026 · revisado em 13/10/2026 (login com a conta do CIn, ADR-010) e em 22/10/2026 (sem conta
institucional, ADR-011)

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

**Fonte (ADR-011):** a Gerinfra negou a conta institucional em 22/10/2026. Um filtro na caixa
`@cin.ufpe.br` de um integrante da lista encaminha as mensagens para uma conta Gmail do projeto,
e o worker lê essa conta. O encaminhamento para fora foi testado em 22/10/2026 e funciona. Falta
conferir os cabeçalhos (`From`, `Message-ID`, `References`) no primeiro anúncio real
encaminhado. Se o CIn passar a bloquear, a demonstração roda com o corpus local e a questão
volta ao PO.

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
| Mensagem sem corpo de texto (só anexo) | Registra a mensagem com corpo vazio e segue. A US-02 decide: com foto e objeto no assunto, é achado; sem isso, quarentena. |
| Banco indisponível | Worker encerra sem consumir mensagens. Nada é marcado como processado. |
| Duas execuções simultâneas do worker | A segunda detecta execução em andamento e encerra. Sem processamento duplicado. |
| Encaminhamento desfeito (filtro removido ou caixa de origem desativada) | Nenhuma mensagem nova chega, e o worker não distingue isso de uma lista quieta. O site continua no ar com o que já tem. Retomar é refazer o filtro em qualquer caixa inscrita na lista (ver o doc de passagem). Risco R7. |

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
| Pergunta "alguém viu um fone preto?" | **Publica como perdido.** Quem pergunta se alguém viu está procurando. Decisão do PO em 14/10/2026. |
| Texto ambíguo: assunto "[PERDIDO]", corpo "Mouse deixado no Grad02" | Quarentena — pode ser perda ou achado, e publicar na categoria errada torna o item inencontrável. O autor pode resolver em "Meus anúncios" (US-15). |
| Mensagem curta mas válida: "encontrei esse carregador no Grad 05" | **Publica.** Extração fraca não é motivo para reter. Campo vazio é honesto; campo errado não é. |
| Sem texto no corpo, com foto, e o assunto nomeia o objeto ("Garrafa no Grad 5") | **Publica como achado.** Quem perdeu não anuncia só com uma foto. A regra vale só quando o corpo está vazio: com texto, decidem os verbos. Decisão do PO em 14/10/2026 (caso 10 do corpus). |
| Relato de algo já resolvido: "esqueci, já fui buscar, estou registrando porque a portaria pediu" | **Vira item já encerrado**, com a fonte "confirmação do autor". Fica no histórico sem aparecer como aberto. Decisão do PO em 14/10/2026 (caso 8 do corpus). |
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
E isso inclui itens que citam aquele local entre outros ("Grad 5 ou lab de hardware")

Dado que um item foi encerrado por declaração de terceiro (US-10)
Quando ele aparece no catálogo
Então mostra "encerrado segundo terceiro", e não apenas "encerrado"
E continua aparecendo na busca, para quem procura poder conferir

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

Dado que anunciei pela lista e minha mensagem ficou retida em quarentena
Quando acesso "Meus anúncios"
Então vejo essa mensagem marcada como "não entrou no catálogo", com o motivo da retenção
E ela não aparece no catálogo nem em "Meus anúncios" de nenhuma outra pessoa

Dado que estou numa mensagem minha que ficou retida
Quando indico "é um perdido" ou "é um achado"
Então a mensagem vira item, passa pela extração e aparece no catálogo
E a classificação fica registrada como evento, com a fonte "classificação pelo autor"

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
Então quem anunciou recebe um único aviso por conversa, por e-mail privado enviado pela conta
do projeto (ADR-011), com o link do item
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
| Autor nunca classifica a mensagem retida | Ela continua na quarentena, sem nenhum efeito no catálogo. |
| Mensagem retida é uma resposta na thread de outra pessoa | Não aparece em "Meus anúncios". Só a mensagem que abre a thread é anúncio. |
| Alguém tenta ver a mensagem retida de outra pessoa pela API | 403. Mensagem retida é a exceção mais sensível à invariante 5 e deve ser coberta por teste. |
| Aviso enviado para a lista em vez de para o autor | **Defeito grave** de privacidade. Deve ser coberto por teste. |
| Recibo enviado várias vezes para a mesma conversa | **Defeito.** Deve haver verificação por conversa antes do envio. |

> **Decidido pelo PO em 14/10/2026:**
> 1. **O catálogo fica aberto para leitura, sem login.** O login é exigido só para anunciar e
>    para gerir os próprios anúncios. Quem não entrou vê só os campos extraídos. O texto
>    original aparece apenas para quem entrou com a conta do CIn (ver US-04 e US-05).
> 2. **O autor pode encerrar a partir de `aberto`**, pelo site ou por mensagem na thread. É a
>    exceção à invariante 2: uma declaração de desfecho não precisa passar por `reivindicado`.
>    Depois, o gabarito do corpus (caso 19) estendeu a exceção à declaração de terceiro na
>    thread, com a fonte "terceiro" e confiança média (US-10).
> 3. **A mensagem retida aparece para o autor em "Meus anúncios", e ele resolve** dizendo se é
>    perda ou achado. É a exceção única à invariante 5. Isso aumenta o esforço desta história,
>    e a estimativa precisa ser revista no refinamento.

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

Dado que o item foi publicado
Quando vejo a confirmação
Então o site abre o e-mail pronto para a lista, saindo da minha conta (US-07)
```

> **Decidido pelo PO em 22/10/2026:** sai o aviso sobre o `Reply-To`, decidido em 14/10. Com a
> US-07 no formato de e-mail pronto (ADR-011), a pessoa envia da própria conta e vê o
> destinatário antes de enviar. Não há mais conta do sistema nem `Reply-To`.
>
> **Entrega junto com a US-07:** o cadastro pelo site não vai ao ar sem o e-mail pronto, para
> que quem só usa e-mail continue vendo esses anúncios.

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

**Estimativa:** 5 (a rever no refinamento: o formato ficou mais simples)

**Formato decidido pelo PO em 22/10/2026 (ADR-011):** o sistema não posta na lista. O site abre
um e-mail pronto, e a própria pessoa o envia da conta dela. Não há conta do sistema, permissão de
postar nem `Reply-To`: as respostas chegam à pessoa porque foi ela quem enviou. Entrega junto com
a US-06.

### Critérios de aceitação

```gherkin
Dado que acabei de cadastrar um item pelo site
Quando vejo a confirmação
Então o site abre um e-mail pronto para achados-perdidos@cin.ufpe.br, saindo da minha conta do CIn
E o assunto é padronizado
E o corpo traz descrição, local, onde deixei o objeto, o link do item no catálogo e um código do item
E eu posso revisar o texto antes de enviar

Dado que enviei o e-mail
Quando alguém responde a ele
Então a resposta chega a mim, como em qualquer e-mail que mando para a lista

Dado que o worker lê na lista o e-mail que enviei
Quando encontra o código do item
Então liga a thread ao item já publicado
E não cria item novo nem passa a mensagem pela classificação

Dado que fechei o e-mail sem enviar
Quando acesso "Meus anúncios"
Então o item continua no catálogo
E aparece marcado como "ainda não foi para a lista", com um botão para abrir o e-mail de novo
E a marcação some quando o worker ligar o e-mail ao item
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Navegador sem programa de e-mail configurado | O link abre a tela de escrever do Gmail, já que toda conta do CIn é Google. Se nem isso abrir, a confirmação mostra o texto para copiar. |
| Pessoa apaga ou altera o código ao revisar | O worker não reconhece o código, e a mensagem segue o fluxo normal de classificação. Pode surgir um item duplicado, que a US-17 sinaliza. |
| Pessoa envia o e-mail duas vezes | As duas threads se ligam ao mesmo item pelo código. Nenhum item novo é criado. |
| Lista atrasa ou modera a mensagem | O item já está no catálogo. A marcação some quando o worker ler o e-mail. |

---

## US-09 · Pedir remoção de um item em que apareço

**Como** pessoa citada em um anúncio que não publiquei,
**quero** pedir que o item seja removido do catálogo,
**para que** meu nome não fique indexado publicamente.

**Estimativa:** 2

**Canal (ADR-011):** sem alias institucional, o contato do rodapé é um endereço `+remocao` da
conta Gmail do projeto. Quem atende é quem estiver com a conta, conforme o doc de passagem.

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
Quando alguém que não é o autor responde declarando o desfecho ("resolvido, ela achou")
Então a situação passa direto a encerrado
E a origem do encerramento é registrada como "terceiro", com confiança média
E o catálogo mostra o item como "encerrado segundo terceiro"

Dado que um item está aberto
Quando alguém responde com uma reivindicação fraca ("acredito que pode ser minha")
Então a situação passa a reivindicado

Dado que um item já está encerrado
Quando chega nova resposta na conversa
Então a situação não é alterada
E o evento é registrado no histórico
```

### Casos de falha

| Falha | Comportamento esperado |
|---|---|
| Detecção equivocada de devolução | **Falha mais cara do sistema** — mente para quem procura. Mitigação: só avança com alta confiança; autor corrige entrando com a conta do CIn (US-15). |
| Terceiro declara desfecho por engano ou em piada ("resolvido!") | O item é encerrado e não volta, porque a situação nunca retrocede. A fonte "terceiro" fica registrada, e o catálogo mostra **"encerrado segundo terceiro"**, para quem procura não descartar o item. Decisão do PO em 14/10/2026. |
| Resposta ambígua ("achei!") | Não altera a situação. Registra o evento e mantém o estado anterior. |
| Reivindicação sem retirada posterior | Item permanece visível no catálogo mostrando há quanto tempo está reivindicado. Não reabre nem encerra sozinho. |
| Confirmação chega por fora da lista | Não é detectada. Encerramento depende do autor logado (US-15). Limitação conhecida. |

---

# COULD

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

> **Linha de base (decisão do PO em 14/10/2026):** antes do sistema, só **8,6%** das threads
> da lista registravam desfecho (37 de 429, de mai/2025 a out/2026,
> `docs/corpus/ANALISE-CORPUS.md` §4.5). A página compara a fração de itens encerrados com
> esse número, e declara que as duas medidas contam só desfechos registrados.

---

## US-16 · Refletir o descarte institucional no catálogo

**Como** pessoa que procura um objeto,
**quero** saber quando um setor avisou que descartou o que não foi retirado,
**para que** eu não procure por algo que já não existe.

**Estimativa:** a definir
**Origem:** o corpus tem dois avisos de descarte com prazo, em ago/2025 e em dez/2025 (este da
SecGrad). Hoje os itens desse lote continuam `aberto` no catálogo depois do descarte.

> **Pendente com o PO:** o Luiz vai levantar com o CIn qual é a regra de descarte, quem decide
> e com que frequência. Os critérios de aceitação só serão escritos depois disso. Qualquer
> que seja a regra, a invariante 7 continua valendo: o sistema não inventa prazo, só registra
> um descarte que a instituição declarou.

---

## US-17 · Sinalizar possíveis anúncios duplicados

**Como** pessoa que procura ou que anunciou um objeto,
**quero** ver quando dois anúncios parecem ser do mesmo objeto,
**para que** eu não trate como dois casos o que é um só.

**Estimativa:** a definir
**Origem:** gabarito do corpus, casos 15 e 17. O corpus tem 12 anúncios repetidos pela mesma
pessoa e 10 casos em que pessoas diferentes anunciam o mesmo objeto, cerca de 5% das threads.

### Critérios de aceitação (aprovados pelo PO em 14/10/2026)

```gherkin
Dado que dois itens têm o mesmo objeto, um local em comum e datas próximas
Quando aparecem no catálogo
Então cada um mostra um aviso "talvez seja o mesmo objeto que", com link para o outro
E nenhum dos dois é fundido nem ocultado automaticamente

Dado que os dois itens têm o mesmo autor
Quando ele acessa "Meus anúncios"
Então vê o aviso de possível duplicata
E pode remover um deles (US-15)
```

> A comparação é por campos extraídos e regra determinística, sem LLM (invariante 6). A
> decisão 4 continua valendo: o sistema sinaliza, mas não decide sozinho que dois anúncios são
> o mesmo objeto, porque fundir errado é pior que mostrar duas vezes.

---

## US-18 · Ligar "na aula de X" à sala da disciplina

**Como** pessoa que perdeu algo durante uma aula,
**quero** que um anúncio como "esqueci na aula de Programação" apareça no filtro da sala certa,
**para que** quem procura pelo local encontre o item.

**Estimativa:** a definir
**Origem:** gabarito do corpus, caso 24. Há 13 anúncios cujo local é dado pela aula ou evento,
e hoje o campo local fica vazio nesses casos.

### Critérios de aceitação (aprovados pelo PO em 14/10/2026)

```gherkin
Dado que o texto cita uma disciplina ("na aula de Algoritmos") e não cita sala
Quando a extração termina
Então o local é preenchido com a sala em que a disciplina acontece no semestre
E o item registra que o local veio da grade horária, e não do texto

Dado que a disciplina não está na grade carregada
Quando a extração termina
Então o local continua vazio
```

> **Depende de levantamento (Luiz):** a grade horária do CIn com disciplina e sala por
> semestre (SCRUM-64). O PO avalia que essa informação é fácil de obter. Sem a grade, a
> história não começa.
>
> **Atenção à invariante 3:** a grade preenche o `local` (onde foi perdido), e não a
> `localização` (onde o objeto está). A localização continua só por declaração explícita.

---

# WON'T — fora desta entrega

| Item | Motivo |
|---|---|
| **US-08 · Receber o recibo e poder corrigir o item** (link com token) | **Descontinuada em 13/10/2026, substituída pela US-15.** O token evitava login, mas o login com a conta Google do CIn não cria conta nem senha para o projeto manter. Ele também elimina o risco de link encaminhado e de acesso perdido. Ver ADR-010. O texto original da história está no histórico do git. |
| **US-11 · Importar o histórico da lista** | **Decidido pelo PO em 22/10/2026.** O Takeout do grupo dependia da Gerinfra, que negou os pedidos. Importar da caixa pessoal publicaria nomes de terceiros de anos atrás e, sem expiração por tempo (invariante 7), deixaria os anúncios antigos `aberto` para sempre. O corpus segue só como base de teste. |
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

US-15 (login) ──→ US-06 (cadastro) + US-07 (e-mail pronto para a lista) [entregues juntas]

US-12, US-13 ─ independentes, COULD
```

**Caminho crítico:** US-01 → US-02 → US-03 → US-04. Com essas quatro, existe produto
demonstrável.

---

# Riscos registrados

| # | Risco | Natureza | Mitigação |
|---|---|---|---|
| R1 | ~~Permissão de postar não ser concedida~~ | organizacional | **Extinto em 22/10/2026.** A US-07 não posta mais em nome do sistema: a pessoa envia da própria conta (ADR-011) |
| R2 | Arquivamento do grupo estar desativado | externa | **Materializado em 22/10/2026:** a Gerinfra negou os pedidos. US-11 em WON'T; o catálogo nasce vazio e cresce |
| R3 | Detecção equivocada de devolução | técnica | Só avança com alta confiança; correção pelo autor logado (US-15) |
| R4 | Ausência de responsável após dezembro | organizacional | **Aceito pelo PO.** Sistema desenhado para operar sem supervisão |
| R5 | Pedido de remoção sem destinatário | legal | Decorre de R4. O alias institucional foi negado. O contato é o endereço `+remocao` da conta do projeto, que passa junto com a conta (ADR-011) |
| R6 | Volume insuficiente para demonstrar valor | produto | ~25 itens/mês segundo o corpus, mas quase zero em janeiro e julho: a demonstração não pode cair nas férias. A US-11, que ajudaria, foi para WON'T |
| R7 | A leitura depende de um filtro de encaminhamento na caixa de um integrante | organizacional | **Aceito pelo PO em 22/10/2026.** Um doc de passagem, sem credenciais, explica como transferir a conta do projeto e refazer o filtro em qualquer caixa inscrita na lista. Fere o R6 em parte: o catálogo para de receber se ninguém assumir, mas retomar é barato |
| R8 | O CIn bloquear o encaminhamento para fora ou o login por app externo | externa | **Encaminhamento testado em 22/10/2026: funciona.** Se o CIn passar a bloquear, a demonstração usa o corpus local e a questão volta ao PO. **Login ainda não testado:** se falhar, a US-15 fica bloqueada e a questão também volta ao PO |
