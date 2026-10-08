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
- **`situacao`:** `aberto`, `reivindicado` ou `encerrado`. Nenhum outro valor.
- **`localizacao`:** `no local`, `com quem achou`, `caixa do bloco A/E` ou `devolvido`. Só muda por declaração.
- **Não existe endpoint de `DELETE` para item.** Existe ocultar.
