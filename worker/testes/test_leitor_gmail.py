"""US-01 · fonte Gmail (SCRUM-50) com a API simulada: respostas JSON em testes/fixtures/gmail/.

Os e-mails dos fixtures são fictícios (fic.*@cin.ufpe.br). Nenhum teste fala com o Google.
"""
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import httplib2
from googleapiclient.errors import HttpError

from worker.__main__ import SAIDA_FONTE, executar_uma_vez
from worker.fonte import CredencialInvalida, FonteIndisponivel
from worker.leitor_gmail import CONSULTA_PADRAO, LeitorGmail, carregar_credenciais, consulta_com_corte
from worker.pipeline import Pipeline
from worker.testes.apoio import URL_TESTE, TesteComBanco

FIXTURES = Path(__file__).parent / "fixtures" / "gmail"


def carregar(nome):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


class Requisicao:
    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro = resposta, erro

    def execute(self, num_retries=0):
        if self.erro is not None:
            raise self.erro
        return self.resposta


class GmailSimulado:
    """Imita `service.users().messages()` com list/get. Registra as consultas feitas."""

    def __init__(self, erro_no_list=None, erro_no_get=None):
        self.paginas = {None: carregar("lista_pagina_1.json"), "pagina-2": carregar("lista_pagina_2.json")}
        self.mensagens = carregar("mensagens.json")
        self.erro_no_list, self.erro_no_get = erro_no_list, erro_no_get
        self.consultas = []
        self.alteracoes = 0  # modify/trash/delete: o leitor nunca deve chamar

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, userId, q, pageToken=None, maxResults=None):
        self.consultas.append(q)
        return Requisicao(self.paginas[pageToken], self.erro_no_list)

    def get(self, userId, id, format):
        assert format == "raw"
        return Requisicao(self.mensagens[id], self.erro_no_get)

    def modify(self, *a, **k):
        self.alteracoes += 1

    trash = delete = modify


def erro_http(status):
    return HttpError(httplib2.Response({"status": status}), b"{}")


class TestLeitorGmail(unittest.TestCase):
    def test_pagina_e_converte_as_mensagens(self):
        gmail = GmailSimulado()
        mensagens = list(LeitorGmail(servico=gmail).obter_mensagens())
        self.assertEqual([m.id_mensagem for m in mensagens], ["<g1@mail.gmail.com>", "<g2@mail.gmail.com>", "<g3@mail.gmail.com>"])
        self.assertEqual(len(gmail.consultas), 2)  # duas páginas
        anuncio, resposta, direta = mensagens
        self.assertEqual(anuncio.id_conversa, "18f0a1")  # threadId do Gmail
        self.assertEqual(resposta.id_conversa, "18f0a1")
        self.assertEqual(resposta.em_resposta_a, "<g1@mail.gmail.com>")
        self.assertEqual(anuncio.assunto, "Garrafa azul no Grad 5")
        self.assertIn("garrafa azul", anuncio.corpo_texto)
        self.assertEqual(anuncio.data_envio.astimezone(timezone.utc), datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(resposta.corpo_texto.strip(), "É minha! Passo lá hoje.")

    def test_veio_da_lista_sai_do_x_beenthere(self):
        anuncio, resposta, direta = LeitorGmail(servico=GmailSimulado()).obter_mensagens()
        self.assertTrue(anuncio.veio_da_lista)
        self.assertTrue(resposta.veio_da_lista)
        self.assertFalse(direta.veio_da_lista)  # resposta ao aviso, direto para a conta do projeto

    def test_nao_altera_nada_na_caixa(self):
        gmail = GmailSimulado()
        list(LeitorGmail(servico=gmail).obter_mensagens())
        self.assertEqual(gmail.alteracoes, 0)

    def test_consulta_exclui_enviados_e_usa_corte_com_folga(self):
        self.assertEqual(consulta_com_corte(None), CONSULTA_PADRAO)
        ultima = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(consulta_com_corte(ultima), f"{CONSULTA_PADRAO} after:{int(ultima.timestamp()) - 2 * 86400}")
        gmail = GmailSimulado()
        list(LeitorGmail(servico=gmail, ultima_gravacao=lambda: ultima).obter_mensagens())
        self.assertTrue(all("-in:sent" in q and "after:" in q for q in gmail.consultas))

    def test_credencial_recusada_vira_credencial_invalida(self):
        for status in (401, 403):
            with self.assertRaises(CredencialInvalida):
                list(LeitorGmail(servico=GmailSimulado(erro_no_list=erro_http(status))).obter_mensagens())

    def test_api_fora_vira_fonte_indisponivel(self):
        with self.assertRaises(FonteIndisponivel):
            list(LeitorGmail(servico=GmailSimulado(erro_no_list=erro_http(503))).obter_mensagens())
        with self.assertRaises(FonteIndisponivel):
            list(LeitorGmail(servico=GmailSimulado(erro_no_get=OSError("rede"))).obter_mensagens())

    def test_sem_token_pede_autorizacao(self):
        with self.assertRaises(CredencialInvalida) as ctx:
            carregar_credenciais("/caminho/que/nao/existe/token.json")
        self.assertIn("autorizar_gmail", str(ctx.exception))


class TestGmailNoCiclo(TesteComBanco):
    def ciclo(self, gmail):
        pipeline = lambda repo: Pipeline(repo)
        return executar_uma_vez(URL_TESTE, lambda repo: LeitorGmail(servico=gmail, ultima_gravacao=repo.ultima_gravacao), pipeline)

    def test_ciclo_completo_com_o_gmail_simulado(self):
        self.assertEqual(self.ciclo(GmailSimulado()), 0)
        self.assertEqual(self.contar("mensagem_bruta"), 3)
        self.assertEqual(self.consultar("SELECT situacao FROM item WHERE thread_id = '18f0a1'"), [("reivindicado",)])
        self.assertEqual(self.repo.status_processamento("<g3@mail.gmail.com>"), "ignorada")

    def test_segundo_ciclo_e_idempotente_e_usa_o_corte(self):
        self.ciclo(GmailSimulado())
        gmail = GmailSimulado()
        self.ciclo(gmail)
        self.assertEqual(self.contar("mensagem_bruta"), 3)
        self.assertEqual(self.contar("item"), 1)
        self.assertIn("after:", gmail.consultas[0])

    def test_credencial_expirada_encerra_sem_marcar_nada(self):
        codigo = self.ciclo(GmailSimulado(erro_no_list=erro_http(401)))
        self.assertEqual(codigo, SAIDA_FONTE)
        self.assertEqual(self.contar("processamento"), 0)
