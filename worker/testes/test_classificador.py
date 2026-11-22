"""US-02 · portão de duas perguntas do classificador (SCRUM-87).

Cada critério e caso de falha do backlog vira um teste. Os textos vêm do corpus (casos citados) ou
são frases curtas sem dado pessoal.
"""
import unittest

from worker.classificador import classificar


def c(assunto="", corpo="", foto=False, incompleta=False):
    return classificar(assunto, corpo, tem_imagem=foto, thread_incompleta=incompleta)


class TestPortao(unittest.TestCase):
    """SCRUM-87: é achados e perdidos? achado ou perdido?"""

    def test_verbo_no_corpo_vale_mais_que_a_etiqueta_do_assunto(self):
        # Casos 1, 3 e 14: [PERDIDO] / "perdido" no assunto, "encontrei/achado" no corpo.
        for assunto, corpo in [
            ("[PERDIDO] Óculos escuros dourado da RayBan", "Encontrado no grad5 do lado do G5C53"),
            ("[PERDIDO] Boné bege NY e garrafa d'água preta", "Foi achado agora (21/10 às 14:30) na sala E132"),
            ("Crachá perdido no Grad02", "Encontrei o crachá no grad 02, vou deixar na portaria do bloco A"),
        ]:
            r = c(assunto, corpo)
            self.assertEqual((r.destino, r.tipo), ("item", "achado"), assunto)

    def test_alguem_viu_e_perdido(self):
        r = c("Fone preto", "Alguém viu um fone preto? Usei no Grad 5 de manhã.")
        self.assertEqual((r.destino, r.tipo), ("item", "perdido"))

    def test_mensagem_curta_mas_valida_publica(self):
        r = c("Carregador", "encontrei esse carregador no Grad 05")
        self.assertEqual((r.destino, r.tipo, r.faixa), ("item", "achado", "alta"))

    def test_corpo_vazio_com_foto_e_objeto_no_assunto_e_achado(self):
        # Caso 10 (decisão do PO em 14/10/2026).
        r = c("Garrafa no Grad 5", "", foto=True)
        self.assertEqual((r.destino, r.tipo), ("item", "achado"))

    def test_corpo_vazio_e_nada_no_assunto_vai_para_quarentena(self):
        r = c("[ACHADOS E PERDIDOS]", "", foto=True)
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "sem_texto_e_sem_objeto"))
        r = c("", "")
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "sem_texto_e_sem_objeto"))

    def test_corpo_vazio_sem_foto_decide_pelo_verbo_do_assunto(self):
        # Caso 25: "Perdi uma garrafa cinza..." sem corpo e sem anexo.
        r = c("Perdi uma garrafa cinza da Snatley na sala d003 do CCEN", "")
        self.assertEqual((r.destino, r.tipo), ("item", "perdido"))

    def test_algo_ja_resolvido_vira_item_ja_encerrado(self):
        # Caso 8.
        r = c("Retirando item esquecido na área II",
              "Esqueci uma lousinha lcd de mão na sala 5 da área II, já fui buscar e tô registrando pois a portaria pediu.")
        self.assertEqual((r.destino, r.tipo, r.ja_encerrado), ("item", "perdido", True))

    def test_achado_nunca_nasce_encerrado(self):
        r = c("Garrafa", "Encontrei uma garrafa no Grad 5, já peguei e guardei.")
        self.assertFalse(r.ja_encerrado)

    def test_fora_de_tema_vai_para_quarentena(self):
        # Caso 7 (pesquisa), pedido de descadastro e conversa qualquer.
        for assunto, corpo in [
            ("[PESQUISA] Cibersegurança e Sociedade", "Podem me ajudar respondendo o Forms? É anônimo. https://docs.google.com/forms/d/e/X/viewform"),
            ("Re: lista", "Bom dia, como faço para nao receber mais mensagens de achados e perdidos?"),
            ("Almoço", "Alguém sabe se a copa do bloco E está aberta hoje?"),
        ]:
            r = c(assunto, corpo)
            self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "fora_de_tema"), assunto)

    def test_aviso_de_descarte_e_fora_de_tema(self):
        r = c("Itens - Achados e Perdidos - SECGRAD",
              "Estamos com esses itens (achados/perdidos) na secgrad, o prazo de retirada encerra em 19/12. Os itens não retirados serão descartados.")
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "fora_de_tema"))

    def test_mouse_deixado_com_perdido_no_assunto_e_ambiguo(self):
        # Caso 11: a etiqueta sozinha não decide.
        r = c("[PERDIDO]", "Mouse deixado no Grad02", foto=True)
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "direcao_ambigua"))

    def test_negacao_nao_conta_como_achado(self):
        r = c("Fone", "Vim no grad e não encontrei meu fone. Se alguém achar, me avise.")
        self.assertEqual(r.tipo, "perdido")
        self.assertNotIn("verbo_achei", r.sinais["achado"])

    def test_achados_e_perdidos_no_assunto_nao_e_sinal_de_direcao(self):
        r = c("[Achados e Perdidos]", "Bom dia, tudo bem com vocês?")
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "direcao_ambigua"))

    def test_thread_sem_a_mensagem_original_fica_retida(self):
        # Caso 27: só existe a resposta ("Errata").
        r = c("Re: ACHADOS E PERDIDOS", "Errata: estarei deixando na mesa do professor.", incompleta=True)
        self.assertEqual((r.destino, r.motivo_retencao), ("quarentena", "confianca_baixa"))

