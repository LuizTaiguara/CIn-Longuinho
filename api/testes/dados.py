"""Construtores de dados de teste. Só endereços `fic.*@cin.ufpe.br` (corpus anonimizado)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from psycopg import sql

AUTORA = "fic.teste@cin.ufpe.br"
OUTRA_PESSOA = "fic.outra.pessoa@cin.ufpe.br"

AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------

_contador = {"thread": 0, "mensagem": 0}


def criar_item(con, **campos) -> int:
    _contador["thread"] += 1
    valores = {
        "thread_id": f"thread-{_contador['thread']}",
        "tipo": "achado",
        "descricao": "Garrafa térmica azul",
        "local": ["Grad 5"],
        "situacao": "aberto",
        "localizacao": None,
        "setor": None,
        "autor_email": AUTORA,
        "origem": "lista",
        "data_anuncio": AGORA,
    }
    valores.update(campos)
    colunas = list(valores)
    consulta = sql.SQL("INSERT INTO item ({}) VALUES ({}) RETURNING id").format(
        sql.SQL(", ").join(map(sql.Identifier, colunas)),
        sql.SQL(", ").join(sql.Placeholder() * len(colunas)),
    )
    return con.execute(consulta, [valores[c] for c in colunas]).fetchone()["id"]


def criar_mensagem(con, thread_id: str, **campos) -> int:
    _contador["mensagem"] += 1
    valores = {
        "thread_id": thread_id,
        "mensagem_id": f"<msg-{_contador['mensagem']}@teste.invalid>",
        "remetente": f"Pessoa Fictícia <{AUTORA}>",
        "assunto": "Achado: garrafa",
        "corpo": "Achei uma garrafa azul na Grad 5.",
        "data_envio": AGORA,
    }
    valores.update(campos)
    colunas = list(valores)
    consulta = sql.SQL("INSERT INTO mensagem_bruta ({}) VALUES ({}) RETURNING id").format(
        sql.SQL(", ").join(map(sql.Identifier, colunas)),
        sql.SQL(", ").join(sql.Placeholder() * len(colunas)),
    )
    return con.execute(consulta, [valores[c] for c in colunas]).fetchone()["id"]


def criar_retida(con, mensagem_id: int, thread_id: str, motivo: str = "direcao_ambigua", resolvida=False) -> int:
    return con.execute(
        "INSERT INTO quarentena (thread_id, mensagem_bruta_id, motivo_retencao, grau_confianca, resolvida)"
        " VALUES (%s, %s, %s, 0.4, %s) RETURNING id",
        [thread_id, mensagem_id, motivo, resolvida],
    ).fetchone()["id"]


def antes(**delta) -> datetime:
    return AGORA - timedelta(**delta)
