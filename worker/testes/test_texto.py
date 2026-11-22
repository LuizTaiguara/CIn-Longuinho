"""Limpeza de texto antes de classificar (SCRUM-87): citações, encaminhamentos, assinaturas."""
import unittest

from worker.texto import etiquetas_do_assunto, limpar_assunto, limpar_corpo, normalizar


class TestTexto(unittest.TestCase):
    def test_tira_citacao_do_gmail_em_portugues(self):
        corpo = (
            "Oi, é meu\nVocê deixou pelo Grad 4?\n\nEm ter., 6 de out. de 2026, 07:51, Fulano de Tal\n"
            "<fic.marcelo.vasconcelos@cin.ufpe.br> escreveu:\n\n> Batom perdido\n"
        )
        self.assertEqual(limpar_corpo(corpo), "Oi, é meu\nVocê deixou pelo Grad 4?")

    def test_tira_citacao_em_ingles_e_frances(self):
        self.assertEqual(limpar_corpo("Pode mandar o verso?\n\nOn Fri, Nov 14, 2025, 13:08 Fulano\n<x@y.z> wrote:\n\n> texto"), "Pode mandar o verso?")
        self.assertEqual(limpar_corpo("a nota é minha\n\nLe ven. 14 nov. 2025 à 13:10, Fulano\n<x@y.z> a écrit :\n\n> texto"), "a nota é minha")

    def test_encaminhamento_em_espanhol_mantem_o_texto_e_tira_o_cabecalho(self):
        corpo = (
            "---------- Mensaje reenviado ---------\nDe: Fulana <fic.patricia.nogueira@cin.ufpe.br>\n"
            "Fecha: El jue, 10 sept 2026 a la(s) 19:28\nAsunto: Achados e Perdidos\nPara: Alunos <alunos-grad-l@cin.ufpe.br>, Alunos da\n"
            "Pós-Graduação <alunos-pos-l@cin.ufpe.br>\n\nPerdi uma garrafa azul no Bloco E."
        )
        self.assertEqual(limpar_corpo(corpo), "Perdi uma garrafa azul no Bloco E.")

    def test_resposta_com_encaminhamento_fica_so_com_o_texto_novo(self):
        corpo = "Reforço o pedido.\n\n---------- Forwarded message ---------\nDe: X <x@y.z>\n\nPerdi a mochila."
        self.assertEqual(limpar_corpo(corpo, so_texto_novo=True), "Reforço o pedido.")

    def test_tira_assinatura_e_imagens(self):
        corpo = "Tem uma bolsa perdida.\n[image: image.png]\n--\n*Atenciosamente,*"
        self.assertEqual(limpar_corpo(corpo), "Tem uma bolsa perdida.")

    def test_assunto_sem_prefixo_e_sem_etiquetas(self):
        self.assertEqual(limpar_assunto("Re: [staff] Re: Garrafas no E112"), "Garrafas no E112")
        self.assertEqual(limpar_assunto("[ACHADOS E PERDIDOS] - Mouse Preto"), "Mouse Preto")
        self.assertEqual(limpar_assunto("[PERDIDO]"), "")
        self.assertEqual(etiquetas_do_assunto("Re: [msc] [ACHADO] Nota"), ["msc", "achado"])

    def test_normalizar_tira_acento_e_maiuscula(self):
        self.assertEqual(normalizar("  Crachá  no GRAD 5 "), "cracha no grad 5")
