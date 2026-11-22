"""US-01 · trava e as cinco falhas do backlog (SCRUM-86).

| Falha | Teste |
|---|---|
| Credencial expirada ou revogada | test_credencial_expirada_registra_e_encerra_sem_marcar_nada |
| API do Gmail indisponível | test_fonte_indisponivel_encerra_e_o_proximo_ciclo_recupera |
| Mensagem sem corpo de texto | test_mensagem_sem_corpo_e_registrada_com_corpo_vazio |
| Banco indisponível | test_banco_indisponivel_encerra_sem_consumir_a_fonte |
| Duas execuções simultâneas | test_segunda_execucao_simultanea_encerra_sem_escrever |
"""
import logging
import unittest
from pathlib import Path

import psycopg

from worker.__main__ import SAIDA_BANCO, SAIDA_FONTE, SAIDA_OK, executar_uma_vez
from worker.banco import Repositorio
from worker.fonte import CredencialInvalida, FonteIndisponivel
from worker.leitor_local import LeitorArquivoLocal
from worker.registro import FiltroSemEmail, mascarar_emails
from worker.testes.apoio import URL_TESTE, FonteFalsa, TesteComBanco, mensagem


class TestFalhas(TesteComBanco):
    def test_segunda_execucao_simultanea_encerra_sem_escrever(self):
        outra_execucao = psycopg.connect(URL_TESTE)
        try:
            self.assertTrue(Repositorio(outra_execucao).tentar_trava())
            fonte = FonteFalsa([mensagem(1, veio_da_lista=False)])
            with self.assertLogs("worker", level="INFO") as registros:
                codigo = executar_uma_vez(URL_TESTE, lambda repo: fonte)
            self.assertEqual(codigo, SAIDA_OK)
            self.assertFalse(fonte.consultada)
            self.assertEqual(self.contar("mensagem_bruta"), 0)
            self.assertEqual(self.contar("processamento"), 0)
            self.assertIn("em andamento", "\n".join(registros.output))
        finally:
            outra_execucao.close()
        # Liberada a trava (a sessão fechou), a próxima execução roda normalmente.
        self.assertEqual(executar_uma_vez(URL_TESTE, lambda repo: FonteFalsa([mensagem(1, veio_da_lista=False)])), SAIDA_OK)
        self.assertEqual(self.contar("processamento"), 1)

    def test_banco_indisponivel_encerra_sem_consumir_a_fonte(self):
        fonte = FonteFalsa([mensagem(1)])
        url_morta = "postgresql://longuinho:longuinho@127.0.0.1:1/longuinho_teste_worker"
        with self.assertLogs("worker", level="ERROR"):
            codigo = executar_uma_vez(url_morta, lambda repo: fonte)
        self.assertEqual(codigo, SAIDA_BANCO)
        self.assertFalse(fonte.consultada)

    def test_credencial_expirada_registra_e_encerra_sem_marcar_nada(self):
        fonte = FonteFalsa([mensagem(1, veio_da_lista=False)], erro=CredencialInvalida("token revogado"), falhar_apos=1)
        with self.assertLogs("worker", level="ERROR") as registros:
            codigo = executar_uma_vez(URL_TESTE, lambda repo: fonte)
        self.assertEqual(codigo, SAIDA_FONTE)
        self.assertIn("credencial", "\n".join(registros.output))
        # O que já foi lido fica guardado como bruto, mas nada é marcado como processado.
        self.assertEqual(self.contar("processamento"), 0)

    def test_fonte_indisponivel_encerra_e_o_proximo_ciclo_recupera(self):
        mensagens = [mensagem(1, veio_da_lista=False), mensagem(2, thread="t2", veio_da_lista=False)]
        fora = FonteFalsa(mensagens, erro=FonteIndisponivel("HTTP 503"), falhar_apos=0)
        with self.assertLogs("worker", level="ERROR"):
            self.assertEqual(executar_uma_vez(URL_TESTE, lambda repo: fora), SAIDA_FONTE)
        self.assertEqual(self.contar("mensagem_bruta"), 0)
        self.assertEqual(self.contar("processamento"), 0)

        self.assertEqual(executar_uma_vez(URL_TESTE, lambda repo: FonteFalsa(mensagens)), SAIDA_OK)
        self.assertEqual(self.contar("processamento"), 2)

    def test_mensagem_sem_corpo_e_registrada_com_corpo_vazio(self):
        caso10 = LeitorArquivoLocal(Path("worker/corpus/casos/10-sem-corpo-so-foto"))
        self.assertEqual(executar_uma_vez(URL_TESTE, lambda repo: caso10), SAIDA_OK)
        corpo, cabecalhos = self.consultar("SELECT corpo, cabecalhos FROM mensagem_bruta")[0]
        self.assertEqual(corpo, "")
        self.assertEqual(cabecalhos["anexos"][0]["tipo_mime"], "image/jpeg")


class TestLogSemEmail(unittest.TestCase):
    def test_filtro_mascara_email_na_mensagem_e_nos_argumentos(self):
        registro = logging.LogRecord("worker", logging.INFO, __file__, 1, "remetente %s", ("fic.ana.lemos@cin.ufpe.br",), None)
        FiltroSemEmail().filter(registro)
        self.assertNotIn("@", registro.getMessage())
        self.assertIn("[e-mail mascarado]", registro.getMessage())

    def test_mascarar_emails(self):
        self.assertEqual(mascarar_emails("de Ana <fic.ana.lemos@cin.ufpe.br>"), "de Ana <[e-mail mascarado]>")
