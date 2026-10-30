"""Testes unitários para o leitor de arquivos locais de e-mail (worker/leitor_local.py)."""
from pathlib import Path
import unittest

from worker.leitor_local import LeitorArquivoLocal


class TestLeitorArquivoLocal(unittest.TestCase):
    """Testa a leitura e decodificação de e-mails locais do corpus."""

    def setUp(self):
        self.diretorio_corpus = Path("worker/corpus/casos")

    def test_diretorio_inexistente_retorna_vazio(self):
        """Valida que um diretório inexistente não quebra a execução e retorna vazio."""
        leitor = LeitorArquivoLocal("caminho/que/nao/existe")
        mensagens = list(leitor.obter_mensagens())
        self.assertEqual(mensagens, [])

    def test_caso01_multipart_com_anexo_e_corpo(self):
        """Valida o caso 01: mensagem com texto e foto anexa."""
        caminho_caso = self.diretorio_corpus / "01-assunto-perdido-corpo-achado" / "01.eml"
        leitor = LeitorArquivoLocal(caminho_caso)
        mensagens = list(leitor.obter_mensagens())

        self.assertEqual(len(mensagens), 1)
        msg = mensagens[0]

        self.assertEqual(msg.id_mensagem, "<caso01.m01@corpus.achados.invalid>")
        self.assertEqual(msg.id_conversa, "199a9ead8208d070")
        self.assertIn("Ana Lemos", msg.remetente)
        self.assertEqual(msg.assunto, "[PERDIDO] Óculos escuros dourado da RayBan")
        self.assertIn("Encontrado no grad5", msg.corpo_texto)
        self.assertEqual(len(msg.anexos), 1)
        self.assertEqual(msg.anexos[0].nome_arquivo, "1000041617.jpg")
        self.assertEqual(msg.anexos[0].tipo_mime, "image/jpeg")
        self.assertTrue(msg.veio_da_lista)

    def test_caso10_sem_corpo_so_foto(self):
        """Valida o caso 10: mensagem sem corpo de texto, contendo apenas foto anexada."""
        caminho_caso = self.diretorio_corpus / "10-sem-corpo-so-foto" / "01.eml"
        leitor = LeitorArquivoLocal(caminho_caso)
        mensagens = list(leitor.obter_mensagens())

        self.assertEqual(len(mensagens), 1)
        msg = mensagens[0]

        self.assertEqual(msg.corpo_texto, "")
        self.assertEqual(len(msg.anexos), 1)
        self.assertEqual(msg.anexos[0].nome_arquivo, "1000060457.jpg")
        self.assertEqual(msg.anexos[0].tipo_mime, "image/jpeg")

    def test_caso20_encaminhado_de_outra_lista_extrai_autor_original(self):
        """Valida o caso 20 (ADR-011): mensagem encaminhada preserva o autor original do anúncio."""
        caminho_caso = self.diretorio_corpus / "20-encaminhado-de-outra-lista"
        leitor = LeitorArquivoLocal(caminho_caso)
        mensagens = list(leitor.obter_mensagens())

        self.assertEqual(len(mensagens), 3)

        # Na mensagem 02 (encaminhada com Fwd:)
        msg_encaminhada = mensagens[1]
        self.assertIn("Fwd:", msg_encaminhada.assunto)
        self.assertIn("Patrícia Helena Duarte Nogueira", msg_encaminhada.remetente)
        self.assertIn("fic.patricia.nogueira@cin.ufpe.br", msg_encaminhada.remetente)
        self.assertEqual(msg_encaminhada.id_conversa, "1a08d70135f437bb")
        self.assertEqual(msg_encaminhada.em_resposta_a, "<caso20.m01@corpus.achados.invalid>")

    def test_caso26_reivindicacao_com_respostas_em_thread(self):
        """Valida mensagens de resposta e encadeamento em thread."""
        caminho_caso = self.diretorio_corpus / "26-reivindicacao-fraca"
        leitor = LeitorArquivoLocal(caminho_caso)
        mensagens = list(leitor.obter_mensagens())

        self.assertEqual(len(mensagens), 2)
        # Ambas devem pertencer à mesma conversa
        self.assertEqual(mensagens[0].id_conversa, mensagens[1].id_conversa)
        self.assertEqual(mensagens[1].em_resposta_a, mensagens[0].id_mensagem)


if __name__ == "__main__":
    unittest.main()
