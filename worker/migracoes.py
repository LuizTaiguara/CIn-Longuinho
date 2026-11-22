"""Cria um banco de teste do zero, aplicando `shared/migrations/` em ordem.

Usado pelos testes e por `python -m worker.avaliar`. Nunca toca o banco principal: só o banco cujo
nome vem de DATABASE_URL_TESTE (padrão: `<banco>_teste_worker`, ver config.url_banco_teste).
"""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

from worker.config import DIRETORIO_MIGRACOES


def _nome_banco(url: str) -> str:
    return urlsplit(url).path.lstrip("/")


def _url_administrativa(url: str) -> str:
    """Mesma conexão, apontando para o banco `postgres` (para criar e apagar o de teste)."""
    return urlunsplit(urlsplit(url)._replace(path="/postgres"))


def recriar_banco_de_teste(url_teste: str, diretorio: Path = DIRETORIO_MIGRACOES) -> None:
    """Apaga e recria o banco de teste e aplica todas as migrações. Recusa nomes sem `teste`."""
    nome = _nome_banco(url_teste)
    if "teste" not in nome:
        raise ValueError(f"recuso recriar {nome!r}: o banco de teste precisa ter 'teste' no nome")
    with psycopg.connect(_url_administrativa(url_teste), autocommit=True, connect_timeout=5) as adm:
        adm.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nome)))
        adm.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
    with psycopg.connect(url_teste, autocommit=True) as conexao:
        for arquivo in sorted(diretorio.glob("*.sql")):
            conexao.execute(arquivo.read_text(encoding="utf-8"))


def limpar_tabelas(conexao: psycopg.Connection) -> None:
    """Esvazia as tabelas entre testes. Só no banco de teste: TRUNCATE não dispara os triggers
    de DELETE, que continuam valendo para o código de verdade."""
    nome = conexao.info.dbname
    if "teste" not in nome:
        raise ValueError(f"recuso limpar {nome!r}: não é banco de teste")
    conexao.execute(
        "TRUNCATE mensagem_bruta, item, evento, quarentena, processamento RESTART IDENTITY CASCADE"
    )
    conexao.commit()
