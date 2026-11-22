# Passagem: o que tem dono e como assumir

O sistema não tem conta institucional (ADR-011). Por isso algumas peças vivem em contas e máquinas de
pessoas. Este documento diz **quais são, quem está com cada uma e como outra pessoa assume**.

**Aqui não há nenhuma credencial**, e não deve haver. Senha, token e chave passam de mão em mão por um
canal privado, nunca por este arquivo, por issue, por PR nem pelo grupo da turma.

**Critério de pronto (SCRUM-108):** alguém de fora da equipe consegue, só com este documento e o acesso
recebido do dono anterior, retomar o recebimento de anúncios.

## Se ninguém assumir

Nada quebra de repente. O catálogo continua no ar com o que já tem, e para de receber anúncios novos.
Nenhum erro aparece para quem visita. É o comportamento previsto (R6, R7): retomar é barato, e este
documento existe para isso.

## Quem está com o quê

Atualize esta tabela **a cada passagem**, por PR. Ela é a parte mais importante do documento.

| Peça | Para que serve | Com quem está | Desde |
|---|---|---|---|
| Conta Gmail do projeto | Recebe a lista, envia o aviso ao autor e o contato, recebe os pedidos de remoção (`+remocao`) | _preencher_ | _preencher_ |
| Filtro de encaminhamento | Leva os e-mails da lista de uma caixa `@cin.ufpe.br` para a conta do projeto | _preencher_ (dono da caixa `@cin`) | _preencher_ |
| Projeto no Google Cloud | Guarda os dois clients OAuth: o do login no site e o da leitura do Gmail | _preencher_ | _preencher_ |
| VPS | Onde o sistema roda | Luiz Taiguara | 22/11/2026 |
| Domínio e DNS | O endereço do catálogo | Luiz Taiguara | 22/11/2026 |
| Repositório no GitHub | O código e estes documentos | Luiz Taiguara (`LuizTaiguara/CIn-Longuinho`) | — |

> As três primeiras linhas estão em branco porque este documento foi escrito sem essa informação
> (22/11/2026). Quem souber, preencha.

## 1. O que o sistema precisa para receber anúncios

Uma cadeia de quatro elos. Se um cai, os anúncios param de chegar:

```
lista achados-perdidos@cin.ufpe.br
   → caixa @cin.ufpe.br de um integrante inscrito na lista
      → filtro do Gmail que encaminha para a conta do projeto
         → worker na VPS, que lê a conta do projeto a cada 5 minutos
```

O worker só aceita mensagem que **passou pela lista**: ele confere o cabeçalho `X-BeenThere`, que precisa
conter `achados-perdidos@cin.ufpe.br` (decisão do PO em 13/11/2026). E-mail mandado direto para a conta do
projeto é guardado, mas não vira anúncio.

## 2. Como refazer o filtro de encaminhamento

Serve qualquer caixa `@cin.ufpe.br` **inscrita na lista**. São dois passos, no Gmail dessa caixa.

**a) Autorizar o endereço de destino.**
*Configurações → Ver todas as configurações → Encaminhamento e POP/IMAP → Adicionar um endereço de
encaminhamento.* Informe o endereço da conta do projeto. O Gmail manda um código de confirmação para a
conta do projeto: quem está com ela precisa abrir o e-mail e confirmar.

**b) Criar o filtro.**
*Configurações → Filtros e endereços bloqueados → Criar novo filtro.*
- Critério: as mensagens da lista. O registrado na SCRUM-108 é `list:achados-perdidos@cin.ufpe.br`, no
  campo "Contém as palavras".
- Ação: **Encaminhar para** o endereço da conta do projeto. Não marque "Excluir".

Depois, confira: mande um e-mail de teste para a lista (ou espere o próximo anúncio) e veja se ele chega
à conta do projeto.

> **Cuidado com o critério (visto em 28/10/2026, ADR-011).** A mensagem chega à caixa por listas
> aninhadas (a de achados e perdidos dentro da de alunos, dentro da da turma), e o cabeçalho `List-ID` é o
> da **última**. Se o filtro por `list:` não pegar nada, use o destinatário como critério:
> `to:achados-perdidos@cin.ufpe.br`. **Falta registrar aqui qual critério está em uso hoje.**

> **O filtro morre com a caixa.** Ele depende de a pessoa continuar inscrita nessa cadeia de listas. A
> lista da turma acaba com a formatura (R7). Antes de se formar ou sair do CIn, o dono do filtro passa o
> encaminhamento para outra caixa.

## 3. Como transferir a conta Gmail do projeto

Quem entrega e quem recebe fazem juntos, de preferência ao vivo:

1. Quem recebe entra na conta com a senha atual.
2. Troca a **senha**.
3. Troca o **telefone** e o **e-mail de recuperação** para os seus (*Conta Google → Segurança*).
4. Confere a **verificação em duas etapas**: tira o aparelho antigo e põe o seu.
5. Em *Segurança → Seus dispositivos*, encerra as sessões que não são suas.
6. Apaga as **senhas de app** antigas e cria uma nova (ela vai para a VPS, item abaixo).
7. Atualiza a tabela "Quem está com o quê".

Trocar a senha da conta **derruba** a senha de app e pode derrubar o token de leitura. Por isso, logo
depois, é preciso atualizar a VPS:

| O que usa a conta | Onde fica na VPS | Como renovar |
|---|---|---|
| Envio de e-mail (contato e aviso ao autor) | `SMTP_USUARIO`, `SMTP_SENHA` e `EMAIL_REMETENTE`, no `.env` | Criar senha de app nova, pôr em `SMTP_SENHA` e rodar `docker compose up -d api` |
| Leitura da lista pelo worker | `worker/.segredos/token.json` e `credenciais.json` | Rodar `python -m worker.autorizar_gmail` numa máquina com navegador e copiar o `token.json` novo para a VPS |
| Endereço de remoção no rodapé | `VITE_EMAIL_REMOCAO`, no `.env` | Só muda se o endereço da conta mudar. Aí: `docker compose up -d --build site` |

O passo a passo de cada um está em `docs/DEPLOY.md`, seção 5.

**Os pedidos de remoção chegam nessa conta**, no endereço `+remocao`. Quem está com a conta é quem atende:
lê o pedido e oculta o anúncio. Não há automação (US-09). Sem ninguém olhando a caixa, o pedido fica sem
resposta: é uma limitação conhecida (ARQUITETURA §3.7).

## 4. Como transferir o projeto no Google Cloud

No Google Cloud Console, em *IAM e administrador → IAM*, o dono atual adiciona a conta de quem recebe com o
papel **Proprietário**. Depois de a pessoa nova confirmar que entra, o dono antigo se remove.

O projeto guarda dois clients OAuth:
- **Aplicativo da Web:** o login "Entrar com a conta do CIn". Depende do domínio: se o domínio mudar, o
  endereço de retorno (`https://<dominio>/api/auth/google/callback`) precisa ser cadastrado de novo.
- **App para computador:** a leitura do Gmail pelo worker.

Se o projeto se perder, dá para criar outro do zero seguindo o `docs/DEPLOY.md`, seções 4 e 5. Ninguém
perde dado: só é preciso trocar as chaves no `.env` e autorizar o Gmail de novo.

## 5. Como transferir a VPS e o domínio

- **VPS:** quem recebe ganha um usuário próprio com acesso por chave SSH; depois o acesso antigo é
  removido. Tudo o que o sistema usa está em `/opt/longuinho` (o código, o `.env`, `worker/.segredos/`), nos
  volumes do Docker e em `/var/backups/longuinho`. O cron fica no usuário que fez o deploy: `crontab -l`.
- **Mudar de VPS:** instalar do zero pelo `docs/DEPLOY.md`, restaurar o último backup e apontar o DNS para
  a máquina nova.
- **Domínio:** a transferência é feita no registrador. Se o domínio for trocado, mudam `DOMINIO` no `.env`
  e o endereço de retorno do login no Google Cloud.

## 6. Como perceber que parou

O sinal é um só: **a lista continua recebendo e-mails e nenhum anúncio novo aparece no catálogo.**
O worker não distingue "ninguém anunciou" de "o encaminhamento foi desfeito" (US-01, casos de falha).

Para achar onde quebrou, siga a cadeia de trás para a frente:

| Pergunta | Onde olhar | Se a resposta for não |
|---|---|---|
| O worker está rodando? | `tail /var/log/longuinho-worker.log` na VPS: há uma linha a cada 5 minutos? | Conferir o cron (`crontab -l`) e se a VPS está de pé |
| O worker consegue ler a conta? | O log diz "credencial da fonte expirada ou revogada"? | Autorizar o Gmail de novo (`docs/DEPLOY.md`, seção 5) |
| Os e-mails chegam à conta do projeto? | Entrar na conta do projeto e ver a caixa de entrada | O problema é o filtro: refazer (seção 2) |
| A caixa `@cin` ainda recebe a lista? | Perguntar ao dono da caixa | A pessoa saiu da lista ou da turma: mover o filtro para outra caixa |

Enquanto isso, o site segue no ar com o que já tem.

## Histórico de passagens

| Data | O que passou | De quem | Para quem |
|---|---|---|---|
| _preencher_ | | | |
