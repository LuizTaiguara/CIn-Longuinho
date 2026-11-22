"""US-02 · confiança em três faixas (SCRUM-88): alta publica, média publica com revisar, baixa retém."""
import unittest

from worker.classificador import classificar


def c(assunto="", corpo="", foto=False, incompleta=False):
    return classificar(assunto, corpo, tem_imagem=foto, thread_incompleta=incompleta)


class TestConfianca(unittest.TestCase):
    """SCRUM-88: três faixas. Alta publica, média publica com revisar, baixa retém."""

    def test_sinal_claro_do_corpo_e_alta_e_nao_pede_revisao(self):
        r = c("Garrafa", "Perdi minha garrafa azul na sala E122.")
        self.assertEqual((r.faixa, r.revisar), ("alta", False))
        self.assertGreater(r.confianca, 0.8)

    def test_so_o_assunto_decide_e_media(self):
        r = c("Fone preto encontrado na antepenúltima fileira do grad5", "", foto=True)
        self.assertEqual((r.destino, r.faixa, r.revisar), ("item", "media", True))

    def test_regra_do_corpo_vazio_e_media(self):
        r = c("Garrafa no Grad 5", "", foto=True)
        self.assertEqual((r.faixa, r.revisar), ("media", True))

    def test_sinais_dos_dois_lados_com_folga_e_media(self):
        r = c("Fone", "Encontrei um fone no Grad 5, guardei comigo. Esqueci de tirar foto.")
        self.assertEqual((r.destino, r.tipo, r.faixa), ("item", "achado", "media"))

    def test_sinais_dos_dois_lados_quase_empatados_e_baixa_e_retem(self):
        r = c("Carregador encontrado", "Perdi meu fone e encontrei um carregador no Grad 5.")
        self.assertEqual((r.destino, r.motivo_retencao, r.faixa), ("quarentena", "confianca_baixa", "baixa"))

    def test_empate_e_direcao_ambigua(self):
        r = c("Fone", "Perdi um fone. Encontrei um fone.")
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "direcao_ambigua"))

    def test_detalhes_nao_carregam_texto_da_mensagem(self):
        r = c("Garrafa", "Perdi minha garrafa. Falar com fic.ana.lemos@cin.ufpe.br")
        self.assertNotIn("@", str(r.detalhes()))
