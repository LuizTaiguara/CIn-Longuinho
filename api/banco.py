"""Acesso ao PostgreSQL: pool de conexões e uma função por consulta nomeada (ADR-008).

Regras que este módulo materializa:
- Invariante 1: nenhuma consulta de leitura devolve `autor_email` nem `remetente` ao Python.
  A autoria é comparada dentro do SQL (`pode_gerir`), e o endereço não sai do banco.
- Invariante 4: nenhuma consulta apaga linha. A única exceção do sistema é `processamento`
  (reprocessamento), usada só na classificação da retida pelo autor (US-15).
- Invariante 5: `itens_publicados` e `item_publicado` filtram `oculto = FALSE`. A quarentena
  não é item, então nunca entra nessas consultas.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout


class BancoIndisponivel(RuntimeError):
    """O banco não respondeu. A API devolve 503 INDISPONIVEL."""


class Banco:
    def __init__(self, database_url: str, timeout: float = 5.0) -> None:
        self._pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=10,
            timeout=timeout,
            open=False,
            kwargs={"row_factory": dict_row},
        )
        self._aberto = False

    def abrir(self) -> None:
        if not self._aberto:
            # wait=False: a API sobe mesmo com o banco fora e responde 503 até ele voltar.
            self._pool.open(wait=False)
            self._aberto = True

    def fechar(self) -> None:
        if self._aberto:
            self._pool.close()
            self._aberto = False

    @contextmanager
    def conexao(self) -> Iterator[psycopg.Connection]:
        self.abrir()
        try:
            with self._pool.connection() as con:
                yield con
        except (PoolTimeout, psycopg.OperationalError) as erro:
            raise BancoIndisponivel(type(erro).__name__) from None


# ---------------------------------------------------------------------------
# Expressões SQL reutilizadas
# ---------------------------------------------------------------------------

# Endereço "puro" e em minúsculas de um campo que pode vir como `Nome <a@b>` ou `a@b`.
# Comparar o endereço inteiro (e não "contém") evita que `ana@...` case com `joana@...`.
def endereco_sql(coluna: str) -> str:
    return (
        f"lower(btrim(coalesce(substring({coluna} from '<\\s*([^<>\\s]+)\\s*>'), {coluna})))"
    )


# Primeira mensagem da thread que veio da lista. Mensagens que o worker marcou como
# `ignorada` em `processamento` (não passaram pela lista, ADR-011) não contam.
SQL_MENSAGEM_DE_ABERTURA = """
    SELECT mb.id, mb.assunto, mb.corpo, mb.data_envio
      FROM mensagem_bruta mb
     WHERE mb.thread_id = {thread}
       AND NOT EXISTS (
             SELECT 1 FROM processamento p
              WHERE p.mensagem_id = mb.mensagem_id AND p.status = 'ignorada')
     ORDER BY mb.data_envio ASC NULLS LAST, mb.id ASC
     LIMIT 1
"""

COLUNAS_ITEM_PUBLICO = """
    i.id, i.tipo::text AS tipo, i.descricao, i.local, i.situacao::text AS situacao,
    i.localizacao::text AS localizacao, i.setor, i.foto_url, i.data_anuncio,
    i.criado_em, i.atualizado_em, i.fonte_encerramento, i.data_situacao, i.revisar,
    i.origem, i.thread_id IS NOT NULL AS tem_thread
"""


# `pode_gerir` é calculado no SQL: o endereço do autor nunca chega ao Python nas leituras.
COLUNAS_ITEM_DETALHE = (
    COLUNAS_ITEM_PUBLICO
    + ", i.thread_id, coalesce("
    + endereco_sql("i.autor_email")
    + " = lower(%s), FALSE) AS pode_gerir"
)


def _escapar_like(termo: str) -> str:
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class FiltrosCatalogo:
    texto: str | None = None
    local: str | None = None
    situacao: str | None = None
    tipo: str | None = None

    def termos(self) -> list[str]:
        return [t for t in (self.texto or "").split() if t]


# ---------------------------------------------------------------------------
# Consultas nomeadas
# ---------------------------------------------------------------------------


def locais_ativos(con: psycopg.Connection) -> list[dict]:
    return con.execute(
        "SELECT nome, bloco FROM local WHERE ativo = TRUE ORDER BY id"
    ).fetchall()


def itens_publicados(
    con: psycopg.Connection,
    filtros: FiltrosCatalogo,
    pagina: int,
    limite: int,
    com_sessao: bool,
) -> tuple[list[dict], int]:
    """Catálogo público: só `oculto = FALSE`, do anúncio mais recente para o mais antigo.

    Sem sessão, a busca por texto nunca consulta `mensagem_bruta` (US-04): o termo só pode
    casar com descrição, locais e setor. Com sessão do CIn, casa também com o corpo da
    mensagem que abriu a thread, depois de tirar dele e-mails e telefones, para a busca não
    revelar o que o mascaramento esconde.
    """
    condicoes = ["i.oculto = FALSE"]
    params: list = []

    if filtros.tipo:
        condicoes.append("i.tipo = %s::tipo_item")
        params.append(filtros.tipo)
    if filtros.situacao:
        condicoes.append("i.situacao = %s::situacao_item")
        params.append(filtros.situacao)
    if filtros.local:
        condicoes.append(
            "EXISTS (SELECT 1 FROM unnest(coalesce(i.local, '{}'::text[])) AS l(nome)"
            " WHERE lower(unaccent(btrim(l.nome))) = lower(unaccent(btrim(%s))))"
        )
        params.append(filtros.local)

    alvo = (
        "lower(unaccent(concat_ws(' ', i.descricao,"
        " array_to_string(coalesce(i.local, '{}'::text[]), ' '), i.setor)))"
    )
    juncao = ""
    if com_sessao and filtros.termos():
        juncao = (
            "LEFT JOIN LATERAL ("
            + SQL_MENSAGEM_DE_ABERTURA.format(thread="i.thread_id")
            + ") abertura ON TRUE"
        )
        corpo_sem_contato = (
            "regexp_replace(regexp_replace(coalesce(abertura.corpo, ''),"
            " '[^[:space:]]+@[^[:space:]]+', ' ', 'g'),"
            " '\\+?[0-9][0-9 ().-]{6,}[0-9]', ' ', 'g')"
        )
        alvo = (
            "lower(unaccent(concat_ws(' ', i.descricao,"
            " array_to_string(coalesce(i.local, '{}'::text[]), ' '), i.setor, "
            + corpo_sem_contato
            + ")))"
        )
    for termo in filtros.termos():
        condicoes.append(f"{alvo} LIKE '%%' || lower(unaccent(%s)) || '%%'")
        params.append(_escapar_like(termo))

    where = " AND ".join(condicoes)
    total = con.execute(
        f"SELECT count(*) AS total FROM item i {juncao} WHERE {where}", params
    ).fetchone()["total"]
    linhas = con.execute(
        f"SELECT {COLUNAS_ITEM_PUBLICO} FROM item i {juncao} WHERE {where}"
        " ORDER BY i.data_anuncio DESC, i.id DESC LIMIT %s OFFSET %s",
        [*params, limite, (pagina - 1) * limite],
    ).fetchall()
    return linhas, total


def item_publicado(
    con: psycopg.Connection, item_id: int, email_sessao: str | None
) -> dict | None:
    """Um item visível no catálogo. Oculto ou inexistente devolve None (vira 404)."""
    return con.execute(
        f"SELECT {COLUNAS_ITEM_DETALHE} FROM item i WHERE i.id = %s AND i.oculto = FALSE",
        [email_sessao, item_id],
    ).fetchone()



def mensagem_de_abertura(con: psycopg.Connection, thread_id: str) -> dict | None:
    """Assunto e corpo da primeira mensagem da thread que veio da lista. Nunca o remetente."""
    return con.execute(
        SQL_MENSAGEM_DE_ABERTURA.format(thread="%s"), [thread_id]
    ).fetchone()
