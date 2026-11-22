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


def sem_contato_sql(expressao: str) -> str:
    """Tira do texto, no SQL, o que `privacidade.mascarar` esconderia (e-mail e telefone)."""
    return (
        "regexp_replace(regexp_replace(coalesce(" + expressao + ", ''),"
        " '[^[:space:]]*@[^[:space:]]*', ' ', 'g'),"
        " '\\+?[0-9][0-9 ().-]{6,}[0-9]', ' ', 'g')"
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

    campos = "concat_ws(' ', i.descricao, array_to_string(coalesce(i.local, '{}'::text[]), ' '), i.setor)"
    juncao = ""
    if com_sessao and filtros.termos():
        juncao = (
            "LEFT JOIN LATERAL ("
            + SQL_MENSAGEM_DE_ABERTURA.format(thread="i.thread_id")
            + ") abertura ON TRUE"
        )
        campos = f"concat_ws(' ', {campos}, abertura.corpo)"
    # O que a resposta mascara não pode ser achado pela busca: e-mails e telefones saem do alvo.
    alvo = f"lower(unaccent({sem_contato_sql(campos)}))"
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



def destinatario_do_contato(con: psycopg.Connection, item_id: int) -> dict | None:
    """O endereço do autor de um item visível, só para entregar o contato (US-05).

    É a única consulta que traz `autor_email` para o Python. O valor vai direto para o
    cabeçalho `To` do e-mail e não é registrado, devolvido nem gravado em evento.
    """
    return con.execute(
        "SELECT id, descricao, autor_email AS destinatario FROM item WHERE id = %s AND oculto = FALSE",
        [item_id],
    ).fetchone()


def mensagem_de_abertura(con: psycopg.Connection, thread_id: str) -> dict | None:
    """Assunto e corpo da primeira mensagem da thread que veio da lista. Nunca o remetente."""
    return con.execute(
        SQL_MENSAGEM_DE_ABERTURA.format(thread="%s"), [thread_id]
    ).fetchone()


# ---------------------------------------------------------------------------
# Área do autor (US-15)
# ---------------------------------------------------------------------------

COLUNAS_ITEM_DO_AUTOR = """
    i.id, i.tipo::text AS tipo, i.descricao, i.local, i.situacao::text AS situacao,
    i.localizacao::text AS localizacao, i.setor, i.foto_url, i.data_anuncio, i.data_situacao,
    i.fonte_encerramento, i.revisar, i.origem, i.codigo, i.oculto,
    (i.origem = 'lista' OR i.thread_id IS NOT NULL) AS foi_para_a_lista
"""


def item_por_id(
    con: psycopg.Connection,
    item_id: int,
    email_sessao: str | None,
    incluir_oculto: bool = False,
    travar: bool = False,
) -> dict | None:
    """Item com `pode_gerir` e `oculto`. Com `travar`, segura a linha até o fim da transação."""
    filtro_oculto = "" if incluir_oculto else " AND i.oculto = FALSE"
    trava = " FOR UPDATE" if travar else ""
    return con.execute(
        f"SELECT {COLUNAS_ITEM_DETALHE}, i.oculto FROM item i WHERE i.id = %s{filtro_oculto}{trava}",
        [email_sessao, item_id],
    ).fetchone()


def itens_do_autor(con: psycopg.Connection, email_sessao: str) -> list[dict]:
    """Todos os itens da pessoa, inclusive os ocultos (segunda exceção da invariante 5)."""
    return con.execute(
        f"SELECT {COLUNAS_ITEM_DO_AUTOR} FROM item i"
        f" WHERE {endereco_sql('i.autor_email')} = lower(%s)"
        " ORDER BY i.data_anuncio DESC, i.id DESC",
        [email_sessao],
    ).fetchall()


# Retida que é da pessoa: a mensagem retida é a que ABRIU a thread (respostas na thread de
# outra pessoa nunca contam) e o remetente dela é o endereço da sessão.
_CONDICAO_RETIDA_DO_AUTOR = (
    f"{endereco_sql('msg.remetente')} = lower(%s)"
    " AND msg.id = (" + SQL_MENSAGEM_DE_ABERTURA.format(thread="msg.thread_id").replace("SELECT mb.id, mb.assunto, mb.corpo, mb.data_envio", "SELECT mb.id") + ")"
)


def retidas_do_autor(con: psycopg.Connection, email_sessao: str) -> list[dict]:
    """Mensagens retidas que abriram uma thread da pessoa e ainda esperam classificação."""
    return con.execute(
        "SELECT q.id, q.motivo_retencao, msg.assunto, msg.corpo,"
        " coalesce(msg.data_envio, msg.criado_em) AS data_envio"
        " FROM quarentena q JOIN mensagem_bruta msg ON msg.id = q.mensagem_bruta_id"
        f" WHERE q.resolvida = FALSE AND {_CONDICAO_RETIDA_DO_AUTOR}"
        " AND NOT EXISTS (SELECT 1 FROM item i WHERE i.thread_id = msg.thread_id)"
        " ORDER BY coalesce(msg.data_envio, msg.criado_em) DESC, q.id DESC",
        [email_sessao],
    ).fetchall()


def retida_do_autor(con: psycopg.Connection, retida_id: int, email_sessao: str) -> dict | None:
    """Uma retida da pessoa (resolvida ou não), travada para a classificação."""
    return con.execute(
        "SELECT q.id, q.resolvida, q.thread_id AS thread_quarentena, msg.thread_id,"
        " msg.mensagem_id, msg.assunto, msg.corpo,"
        " coalesce(msg.data_envio, msg.criado_em) AS data_envio"
        " FROM quarentena q JOIN mensagem_bruta msg ON msg.id = q.mensagem_bruta_id"
        f" WHERE q.id = %s AND {_CONDICAO_RETIDA_DO_AUTOR}"
        " FOR UPDATE OF q",
        [retida_id, email_sessao],
    ).fetchone()


def thread_tem_item(con: psycopg.Connection, thread_id: str) -> bool:
    return con.execute("SELECT 1 FROM item WHERE thread_id = %s", [thread_id]).fetchone() is not None


def criar_item_da_retida(
    con: psycopg.Connection, tipo: str, thread_id: str, autor_email: str, descricao: str, data_anuncio
) -> int:
    return con.execute(
        "INSERT INTO item (tipo, origem, thread_id, autor_email, descricao, data_anuncio)"
        " VALUES (%s::tipo_item, 'lista', %s, %s, %s, coalesce(%s, NOW())) RETURNING id",
        [tipo, thread_id, autor_email, descricao, data_anuncio],
    ).fetchone()["id"]


def resolver_retida(con: psycopg.Connection, retida_id: int, mensagem_id: str) -> None:
    con.execute("UPDATE quarentena SET resolvida = TRUE WHERE id = %s", [retida_id])
    # Única remoção do sistema (Decisão 13): apagar o controle de processamento é o sinal para
    # o worker rodar a extração dessa mensagem no próximo ciclo. Nenhum dado é perdido.
    con.execute("DELETE FROM processamento WHERE mensagem_id = %s", [mensagem_id])


def registrar_evento(
    con: psycopg.Connection,
    item_id: int,
    tipo_evento: str,
    fonte: str,
    aplicado: bool,
    situacao_anterior: str | None = None,
    situacao_nova: str | None = None,
    motivo_recusa: str | None = None,
    detalhes: dict | None = None,
) -> None:
    """Evento append-only. Nunca grava endereço de e-mail em `detalhes`."""
    from psycopg.types.json import Jsonb

    con.execute(
        "INSERT INTO evento (item_id, tipo_evento, situacao_anterior, situacao_nova, fonte,"
        " aplicado, motivo_recusa, detalhes)"
        " VALUES (%s, %s, %s::situacao_item, %s::situacao_item, %s, %s, %s, %s)",
        [
            item_id, tipo_evento, situacao_anterior, situacao_nova, fonte, aplicado,
            motivo_recusa, Jsonb(detalhes) if detalhes is not None else None,
        ],
    )


def atualizar_campos(con: psycopg.Connection, item_id: int, campos: dict) -> None:
    """UPDATE só das colunas editáveis pelo autor (lista fechada)."""
    permitidas = {"descricao", "local", "localizacao", "setor"}
    if not campos or set(campos) - permitidas:
        raise ValueError("campos fora da lista editável")
    atribuicoes = []
    valores = []
    for coluna in sorted(campos):
        tipo = "::localizacao_item" if coluna == "localizacao" else ""
        atribuicoes.append(f"{coluna} = %s{tipo}")
        valores.append(campos[coluna])
    con.execute(
        f"UPDATE item SET {', '.join(atribuicoes)}, atualizado_em = NOW() WHERE id = %s",
        [*valores, item_id],
    )


def encerrar(con: psycopg.Connection, item_id: int) -> None:
    con.execute(
        "UPDATE item SET situacao = 'encerrado', fonte_encerramento = 'confirmação do autor',"
        " atualizado_em = NOW() WHERE id = %s",
        [item_id],
    )


def ocultar(con: psycopg.Connection, item_id: int) -> None:
    con.execute("UPDATE item SET oculto = TRUE, atualizado_em = NOW() WHERE id = %s", [item_id])


# ---------------------------------------------------------------------------
# Cadastro pelo site (US-06, US-07)
# ---------------------------------------------------------------------------

JANELA_CLIQUE_DUPLO_SEGUNDOS = 30


def travar_cadastros_do_autor(con: psycopg.Connection, email_sessao: str) -> None:
    """Serializa os cadastros de uma mesma pessoa, para o clique duplo não criar dois itens."""
    con.execute("SELECT pg_advisory_xact_lock(hashtext('cadastro:' || lower(%s)))", [email_sessao])


def cadastro_recente_igual(
    con: psycopg.Connection, email_sessao: str, tipo: str, descricao: str
) -> int | None:
    linha = con.execute(
        "SELECT id FROM item"
        " WHERE origem = 'site' AND lower(autor_email) = lower(%s) AND tipo = %s::tipo_item"
        " AND descricao = %s AND criado_em > NOW() - make_interval(secs => %s)"
        " ORDER BY id DESC LIMIT 1",
        [email_sessao, tipo, descricao, JANELA_CLIQUE_DUPLO_SEGUNDOS],
    ).fetchone()
    return linha["id"] if linha else None


def codigo_existe(con: psycopg.Connection, codigo: str) -> bool:
    return con.execute("SELECT 1 FROM item WHERE codigo = %s", [codigo]).fetchone() is not None


def criar_item_do_site(
    con: psycopg.Connection,
    codigo: str,
    tipo: str,
    descricao: str,
    local: list[str],
    localizacao: str | None,
    setor: str | None,
    autor_email: str,
) -> int:
    return con.execute(
        "INSERT INTO item (codigo, tipo, descricao, local, localizacao, setor, autor_email,"
        " origem, thread_id, data_anuncio)"
        " VALUES (%s, %s::tipo_item, %s, %s, %s::localizacao_item, %s, %s, 'site', NULL, NOW())"
        " RETURNING id",
        [codigo, tipo, descricao, local, localizacao, setor, autor_email],
    ).fetchone()["id"]


def trocar_foto(con: psycopg.Connection, item_id: int, foto_url: str) -> None:
    con.execute(
        "UPDATE item SET foto_url = %s, atualizado_em = NOW() WHERE id = %s", [foto_url, item_id]
    )


def item_da_foto(con: psycopg.Connection, foto_url: str, email_sessao: str | None) -> dict | None:
    """Item que usa esta foto agora. Serve para não entregar foto de item oculto a terceiros."""
    return con.execute(
        "SELECT i.oculto, coalesce("
        + endereco_sql("i.autor_email")
        + " = lower(%s), FALSE) AS pode_gerir FROM item i WHERE i.foto_url = %s LIMIT 1",
        [email_sessao, foto_url],
    ).fetchone()


def dados_do_email_pronto(con: psycopg.Connection, item_id: int) -> dict | None:
    return con.execute(
        "SELECT id, codigo, origem, tipo::text AS tipo, descricao, local,"
        " localizacao::text AS localizacao, setor FROM item WHERE id = %s",
        [item_id],
    ).fetchone()
