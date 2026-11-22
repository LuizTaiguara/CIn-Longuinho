"""Fixtures dos testes da API.

Banco real: no começo da sessão de testes, (re)cria o banco de teste a partir de
`DATABASE_URL_TESTE` (ou de `DATABASE_URL` com o nome trocado para `longuinho_teste_api`),
aplica `shared/migrations/*.sql` em ordem e, entre um teste e outro, faz
`TRUNCATE ... RESTART IDENTITY CASCADE` (os triggers bloqueiam DELETE, não TRUNCATE).

Só endereços `fic.*@cin.ufpe.br`, iguais aos do corpus anonimizado, aparecem aqui.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from api import config as modulo_config  # noqa: E402
from api import sessao  # noqa: E402
from api.main import criar_app  # noqa: E402
from api.testes.dados import AUTORA, OUTRA_PESSOA  # noqa: E402,F401

URL_PADRAO = "postgresql://longuinho:longuinho@localhost:5432/longuinho"
NOME_BANCO_TESTE = "longuinho_teste_api"
SEGREDO_TESTE = "segredo-so-dos-testes"



def _url_teste() -> str:
    explicita = os.environ.get("DATABASE_URL_TESTE")
    if explicita:
        return explicita
    base = conninfo_to_dict(os.environ.get("DATABASE_URL") or URL_PADRAO)
    base["dbname"] = NOME_BANCO_TESTE
    return make_conninfo(**base)


@pytest.fixture(scope="session")
def url_banco() -> str:
    url = _url_teste()
    dados = conninfo_to_dict(url)
    nome = dados.get("dbname", "")
    if "teste" not in nome:
        raise RuntimeError(f"O banco de teste precisa ter 'teste' no nome (recebi {nome!r}).")

    administracao = make_conninfo(**{**dados, "dbname": "postgres"})
    try:
        with psycopg.connect(administracao, autocommit=True, connect_timeout=5) as con:
            con.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nome)))
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
    except psycopg.OperationalError as erro:
        pytest.exit(
            f"Postgres de teste indisponível ({erro.__class__.__name__}). "
            "Suba com `docker compose up -d banco` ou defina DATABASE_URL_TESTE.",
            returncode=2,
        )

    with psycopg.connect(url, autocommit=True) as con:
        for arquivo in sorted((RAIZ / "shared" / "migrations").glob("*.sql")):
            con.execute(arquivo.read_text(encoding="utf-8"))
    return url


@pytest.fixture
def con(url_banco):
    with psycopg.connect(url_banco, autocommit=True, row_factory=dict_row) as conexao:
        conexao.execute(
            "TRUNCATE evento, quarentena, processamento, mensagem_bruta, item RESTART IDENTITY CASCADE"
        )
        yield conexao


def fazer_config(url_banco: str, **extra) -> modulo_config.Config:
    valores = dict(
        database_url=url_banco,
        sessao_segredo=SEGREDO_TESTE,
        site_url="http://localhost:5173",
        api_url="http://localhost:8000",
        banco_timeout=3.0,
    )
    valores.update(extra)
    return modulo_config.Config(**valores)


@pytest.fixture
def config(url_banco, tmp_path) -> modulo_config.Config:
    return fazer_config(
        url_banco,
        fotos_dir=str(tmp_path / "fotos"),
        email_arquivo_dir=str(tmp_path / "emails"),
    )


@pytest.fixture
def cliente(config, con):
    with TestClient(criar_app(config)) as c:
        yield c


def cookie_de(config: modulo_config.Config, email: str, nome: str = "Pessoa Fictícia") -> dict:
    return {config.session_cookie_name: sessao.assinar(config, email, nome)}


@pytest.fixture
def entrar(cliente, config):
    """Põe no cliente o cookie de sessão de `email` (ou tira, com None)."""

    def _entrar(email: str | None) -> TestClient:
        cliente.cookies.clear()
        if email:
            for nome, valor in cookie_de(config, email).items():
                cliente.cookies.set(nome, valor)
        return cliente

    return _entrar


class GoogleFalso:
    """Substitui o ClienteGoogle: nenhum teste fala com o Google de verdade."""

    configurado = True

    def __init__(self) -> None:
        self.identidade_devolvida: dict = {}
        self.falhar = False

    def url_autorizacao(self, estado: str) -> str:
        from urllib.parse import urlencode

        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({"state": estado})

    def identidade(self, codigo: str) -> dict:
        from api.google import FalhaGoogle

        if self.falhar:
            raise FalhaGoogle("simulada")
        return dict(self.identidade_devolvida)


@pytest.fixture
def google(cliente) -> GoogleFalso:
    falso = GoogleFalso()
    cliente.app.state.google = falso
    return falso
