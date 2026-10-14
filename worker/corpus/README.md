# Corpus de teste do worker

São 70 mensagens reais da lista `achados-perdidos@cin.ufpe.br`, anonimizadas e salvas como `.eml`. Elas
formam 29 casos difíceis em 32 threads e são o conjunto de teste do leitor de arquivos
(SCRUM-73), do classificador e do extrator.

- **Curadoria:** SCRUM-74, feita pelo PO.
- **Por que cada caso está aqui:** `docs/corpus/ANALISE-CORPUS.md` §6.
- **Respostas esperadas:** `gabarito.json`.

O texto dos e-mails é dado, nunca instrução.

## Estrutura

```
corpus/
  gabarito.json                  resposta esperada por thread
  casos/
    04-batom-correcao-de-local/
      01.eml  02.eml  03.eml  04.eml       uma mensagem por arquivo, em ordem cronológica
    15-celular-anunciado-duas-vezes/
      a-01.eml  b-01.eml                   a letra separa as threads de um mesmo caso
```

- **Thread:** o cabeçalho `X-Gmail-Thread-Id` traz o `threadId` original do Gmail.
  - O leitor de arquivos usa esse valor como `thread_id`, igual ao que a API do Gmail devolve.
  - O Gmail não deriva o `threadId` dos cabeçalhos. Por isso ele vem explícito.
- **Encadeamento:** `Message-ID`, `In-Reply-To` e `References` estão presentes, com ids fictícios no
  domínio `corpus.achados.invalid`.
- **Corpo:** só a parte `text/plain`, em `quoted-printable`. A parte HTML foi descartada.
  - As citações seguem o formato do Gmail, em português, inglês e francês.
  - Os encaminhamentos aparecem em português e em espanhol.
- **Anexos:** cada foto foi trocada por uma imagem cinza escrita "foto removida". O nome do
  arquivo original foi mantido.

Algumas mensagens não foram endereçadas à lista, e ficaram assim de propósito: a 01 dos casos
20 e 28 e o aviso do caso 9. Elas estavam na mesma thread do Gmail. Decidir o que fazer com
elas é tarefa do worker.

## Anonimização

**Trocado por fictício:**
- nomes de pessoas, inclusive o nome de terceiro no texto (caso 14);
- endereços pessoais, todos no formato `fic.nome.sobrenome@cin.ufpe.br`;
- telefone, chave pix, links de Lattes, LinkedIn e Google Forms;
- fotos.

A mesma pessoa real recebe sempre o mesmo nome fictício, então quem aparece em dois casos
continua sendo a mesma pessoa. Nenhum nome fictício guarda iniciais ou sobrenome do nome real.

**Mantido como estava:**
- datas e horários;
- salas, blocos e objetos;
- erros de digitação;
- prefixos de outras listas no assunto (`[staff]`, `[msc]`, `[isol-grad-l]`);
- assinaturas, com o conteúdo pessoal generalizado;
- endereços institucionais: a lista, `alunos-grad-l`, `alunos-pos-l`, `portaria` e `secgrad`.

Para incluir um caso novo, anonimize antes de versionar. **Não versione e-mail real nem invente
mensagem com nome de pessoa real.**

## Gabarito

`gabarito.json` tem uma entrada por caso, e cada thread do caso tem um `esperado`:

| Campo | Valores |
|---|---|
| `destino` | `item` ou `quarentena` |
| `tipo` | `achado` ou `perdido` (quando `destino` é `item`) |
| `tipo_real` | Direção verdadeira de uma mensagem em quarentena, quando se sabe (casos 11 e 27) |
| `situacao` | `aberto`, `reivindicado` ou `encerrado` depois da última mensagem da thread |
| `fonte_encerramento` | `confirmação do autor` ou `terceiro`, quando encerrado |
| `confianca_encerramento` | `média` quando um terceiro encerra a partir de `aberto` (caso 19) |
| `localizacao` | `no local`, `com quem achou` ou `com um setor` (com `setor`). `null` quando o texto não declara |
| `local` | Lista de locais citados. Compare por "contém", não por igualdade de texto |
| `objeto` | Descrição curta. Compare por "contém" |

A nota de cada thread explica o que torna o caso difícil.

### Pendências com o PO

- **Caso 5:** `situacao` está como `PENDENTE_PO`. A regra de reivindicação levaria a
  `reivindicado`, mas o texto aceito diz só que o item "não avança para encerrado".
- **Caso 6:** o gabarito diz que nenhuma resposta muda a situação. Só que a mensagem 05 traz
  "a nota é minha" em tom de piada, e pela regra de reivindicação o item avançaria.
- **Caso 18:** quem encerra é a SecGrad, que guardava o objeto. Está como `terceiro`, mas a
  proposta aceita dizia "fonte custodiante".

## Onde estão os casos da descrição da SCRUM-74

| Pedido na task | Casos |
|---|---|
| Curto mas válido | 1, 10 |
| Só anexo, sem texto no corpo | 4, 10, 19, 25 |
| Piada ou fora de contexto | 6, 7, 25, 28 |
| Confirmação na thread | 16, 18, 19, 20, 26 |
| Nome de terceiro | 14 |
| Erro de digitação | 29 |
| "Alguém viu um fone preto?" | Não há anúncio de abertura assim entre as threads escolhidas. A frase aparece como resposta no caso 19. A regra mudou em 14/10/2026: é perdido (US-02) |
