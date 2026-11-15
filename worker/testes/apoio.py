"""Apoio comum aos testes que usam o banco.

Os testes rodam contra o Postgres do `docker compose up -d banco`, num banco próprio
(`DATABASE_URL_TESTE`, padrão `<banco>_teste_worker`), recriado das migrações a cada execução da
suíte. Sem Postgres, esses testes são pulados com o motivo.

Endereços usados aqui são só os fictícios do corpus (`fic.*@cin.ufpe.br`) e o da lista.
"""
import os
import unittest
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

import psycopg

from worker.banco import Repositorio
from worker.config import carregar_dotenv, url_banco_teste
from worker.fonte import AnexoMensagem, FonteMensagens, MensagemFonte
from worker.migracoes import limpar_tabelas, recriar_banco_de_teste

carregar_dotenv()
URL_PADRAO = "postgresql://longuinho:longuinho@localhost:5432/longuinho"
URL_TESTE = os.environ.get("DATABASE_URL_TESTE") or url_banco_teste(
    os.environ.get("DATABASE_URL") or URL_PADRAO
)

LISTA = "achados-perdidos@cin.ufpe.br"
AUTORA = "Ana Lemos <fic.ana.lemos@cin.ufpe.br>"
OUTRA_PESSOA = "Bruno Tavares <fic.bruno.tavares@cin.ufpe.br>"
TERCEIRA_PESSOA = "Carla Menezes <fic.carla.menezes@cin.ufpe.br>"

_estado = {"preparado": False, "erro": None}


def preparar_banco() -> Optional[str]:
    """Recria o banco de teste uma vez por execução. Devolve o motivo se não der."""
    if not _estado["preparado"]:
        _estado["preparado"] = True
        try:
            recriar_banco_de_teste(URL_TESTE)
        except Exception as erro:  # sem Postgres: os testes de banco são pulados
            _estado["erro"] = f"Postgres de teste indisponível ({type(erro).__name__}). Rode `docker compose up -d banco`."
    return _estado["erro"]


class TesteComBanco(unittest.TestCase):
    """Cada teste começa com as tabelas vazias e uma conexão nova."""

    @classmethod
    def setUpClass(cls):
        motivo = preparar_banco()
        if motivo:
            raise unittest.SkipTest(motivo)

    def setUp(self):
        self.conexao = psycopg.connect(URL_TESTE)
        limpar_tabelas(self.conexao)
        self.repo = Repositorio(self.conexao)

    def tearDown(self):
        self.conexao.close()

    def consultar(self, sql: str, parametros: tuple = ()) -> List[tuple]:
        with self.conexao.cursor() as cur:
            cur.execute(sql, parametros)
            linhas = cur.fetchall()
        self.conexao.commit()
        return linhas

    def contar(self, tabela: str) -> int:
        return self.consultar(f"SELECT count(*) FROM {tabela}")[0][0]


class FonteFalsa(FonteMensagens):
    """Fonte em memória. Pode falhar no meio da leitura para simular Gmail fora ou credencial."""

    def __init__(self, mensagens: Iterable[MensagemFonte] = (), erro: Optional[Exception] = None, falhar_apos: int = 0):
        self.mensagens = list(mensagens)
        self.erro = erro
        self.falhar_apos = falhar_apos
        self.consultada = False

    def obter_mensagens(self):
        self.consultada = True
        for i, m in enumerate(self.mensagens):
            if self.erro is not None and i >= self.falhar_apos:
                raise self.erro
            yield m
        if self.erro is not None and self.falhar_apos >= len(self.mensagens):
            raise self.erro


_BASE = datetime(2026, 10, 1, 9, 0, tzinfo=timezone(timedelta(hours=-3)))


def mensagem(
    n: int,
    thread: str = "t1",
    remetente: str = AUTORA,
    assunto: str = "Garrafa no Grad 5",
    corpo: str = "Encontrei uma garrafa azul no Grad 5.",
    minutos: int = 0,
    veio_da_lista: bool = True,
    em_resposta_a: Optional[str] = None,
    anexos: Optional[List[AnexoMensagem]] = None,
) -> MensagemFonte:
    """Monta uma mensagem de teste com Message-ID previsível (`<tN.mN@teste.invalid>`)."""
    return MensagemFonte(
        id_mensagem=f"<{thread}.m{n}@teste.invalid>",
        id_conversa=thread,
        remetente=remetente,
        destinatarios=[LISTA] if veio_da_lista else ["alunos-grad-l@cin.ufpe.br"],
        assunto=assunto,
        corpo_texto=corpo,
        data_envio=_BASE + timedelta(minutes=minutos if minutos else n),
        veio_da_lista=veio_da_lista,
        em_resposta_a=em_resposta_a,
        anexos=anexos or [],
    )


FOTO = AnexoMensagem(nome_arquivo="foto.jpg", tipo_mime="image/jpeg", conteudo=b"\xff\xd8 foto removida")
