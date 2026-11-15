# shared/ — contrato da API e schema (ÁREA PROTEGIDA)

Vale além do `AGENTS.md` da raiz. **Revisor obrigatório: Miguel.**

## O que vive aqui

- Contrato da API REST (contract-first, F-01), com o mock publicado junto.
- Schema do PostgreSQL e as entidades:
  - `mensagem_bruta`
  - `item`
  - `evento`
  - `quarentena`
  - `processamento`
  - tabela de locais
- Modelos importados pelo worker (Python). O site usa só o contrato.

## Por que é protegido

- São duas linguagens, então as estruturas de dados existem em dois lugares.
- Mudar o contrato sem aviso quebra o outro subgrupo em silêncio. Esse é o item que trava mais gente (ADR-008).

## Antes de editar qualquer arquivo daqui

1. **Avise a pessoa.** Diga que é área protegida e qual o impacto no worker e no site.
2. Verifique se a mudança é **de produto** (campo novo visível, regra de visibilidade, estado novo).
   - Se for, pare e mande levar ao PO (seção "Decisões de produto" na raiz).
3. Atualize **contrato e mock juntos**. Contrato sem mock atualizado quebra o front.
4. O PR precisa de revisão do Miguel. Diga isso na descrição do PR.

## Invariantes que o contrato materializa

- **Nenhum endpoint tem campo de e-mail de quem anunciou.** Nem opcional, nem "só para debug".
- **Nenhum endpoint de leitura retorna** item em quarentena ou oculto.
  - Há duas exceções, ambas só em `GET /eu/itens` e só para o próprio autor (sessão do CIn
    igual ao remetente). Ninguém mais vê esses registros.
    - A mensagem retida que **abriu** uma thread dele vem marcada como fora do catálogo e com
      o motivo, para ele dizer se é perda ou achado (US-15). Decisão do PO em 14/10/2026.
    - O item que ele ocultou vem com `oculto: true`, e a ocultação não pode ser desfeita (US-15).
      Decisão do PO em 28/10/2026, registrada como exceção em 13/11/2026.
  - Ver ARQUITETURA §2.3 e invariante 5 da raiz.
- **Todas as rotas ficam sob o prefixo `/api`** (`servers` do contrato). Ex.: `/api/itens`.
- **`situacao`:** `aberto`, `reivindicado` ou `encerrado`. Nenhum outro valor.
- **`localizacao`:** `no local`, `com quem achou`, `com um setor`, `caixa do bloco A/E` ou `devolvido`. Só muda por declaração.
- **Não existe endpoint de `DELETE` para item.** Existe ocultar.

## Vocabulários que worker e API compartilham

São colunas `TEXT` no schema, então o vocabulário vive aqui. Use só estes valores.

| Coluna | Valores |
|---|---|
| `evento.tipo_evento` | `criacao`, `classificacao`, `classificacao_pelo_autor`, `reivindicacao`, `desfecho`, `edicao`, `ocultacao`, `ligacao_thread`, `contato`, `aviso_autor` |
| `evento.fonte` | `confirmação do autor`, `terceiro`, `detecção automática`, `classificação pelo autor`, `cadastro pelo site` |
| `item.fonte_encerramento` | `confirmação do autor`, `terceiro` (CHECK no banco) |
| `item.origem` | `lista`, `site` (CHECK no banco) |
| `processamento.status` | `item`, `evento`, `quarentena`, `ligada` (thread ligada a item do site pelo código), `ignorada` (não passou pela lista) |
| `quarentena.motivo_retencao` | `fora_de_tema`, `direcao_ambigua`, `confianca_baixa`, `sem_texto_e_sem_objeto`, `classificador_indisponivel` |

- Um evento fora de ordem (ex.: reivindicação em item encerrado) é gravado com `aplicado = FALSE` e
  `motivo_recusa`, e o item não muda. O trigger do banco é só rede de segurança: quem confere a
  situação antes do `UPDATE` é o worker ou a API.
- `item.id` sai na API como `item_<id>` (ex.: `item_42`). `quarentena.id` sai como `retida_<id>`.
- O código do item cadastrado pelo site (US-07) tem o formato `AP-XXXXXX`, com 6 caracteres de
  `A-Z2-7`, e vai entre colchetes no assunto do e-mail pronto. O worker o procura no assunto e no corpo.
