"""US-10 · situação do item a partir das respostas na thread (SCRUM-59).

Regras de decisão em `worker/situacao.py`; aqui, o efeito delas no banco quando o pipeline roda.
Os horários são espaçados (meia hora) para a defesa contra zoeira não interferir, salvo no teste dela.
"""
import unittest

from worker.pipeline import Pipeline
from worker.situacao import RespostaAnterior, decidir, thread_virou_zoeira
from worker.testes.apoio import AUTORA, OUTRA_PESSOA, TERCEIRA_PESSOA, FonteFalsa, TesteComBanco, mensagem

QUARTA_PESSOA = "Davi Rocha <fic.davi.rocha@cin.ufpe.br>"
ACHADO = dict(assunto="Garrafa azul no Grad 5", corpo="Encontrei uma garrafa azul no Grad 5.")
PERDIDO = dict(assunto="Perdi meu fone", corpo="Perdi meu fone preto ontem no Grad 3.")


def resposta(n, remetente, corpo, thread="t1", minutos=None):
    return mensagem(
        n, thread=thread, remetente=remetente, assunto="Re: Garrafa azul no Grad 5", corpo=corpo,
        minutos=minutos if minutos is not None else 30 * n, em_resposta_a=f"<{thread}.m1@teste.invalid>",
    )


class TestSituacaoNaThread(TesteComBanco):
    def rodar(self, *mensagens):
        return Pipeline(self.repo).executar_ciclo(FonteFalsa(mensagens))

    def item(self):
        return self.consultar("SELECT situacao, fonte_encerramento, revisar, local, localizacao, setor FROM item")[0]

    def eventos_de_resposta(self):
        return self.consultar(
            "SELECT tipo_evento, fonte, aplicado, situacao_anterior, situacao_nova, motivo_recusa FROM evento "
            "WHERE tipo_evento NOT IN ('classificacao') AND coalesce(detalhes->>'regra', '') <> 'extracao_automatica' "
            "ORDER BY id"
        )

    # ------------------------------------------------------------ reivindicação
    def test_reivindicacao_de_quem_nao_e_o_autor_marca_reivindicado(self):
        r = resposta(2, OUTRA_PESSOA, "Oi! Acho que é minha, deixei lá ontem.")
        self.rodar(mensagem(1, **ACHADO), r)
        self.assertEqual(self.item()[0], "reivindicado")
        self.assertEqual(
            self.eventos_de_resposta(),
            [("reivindicacao", "detecção automática", True, "aberto", "reivindicado", None)],
        )
        self.assertEqual(self.repo.status_processamento(r.id_mensagem), "evento")

    def test_a_data_da_situacao_e_a_da_resposta_e_nao_a_do_processamento(self):
        # US-04: "reivindicado há ..." conta desde a resposta na lista, mesmo se o worker a ler depois.
        r = resposta(2, OUTRA_PESSOA, "Oi! Acho que é minha, deixei lá ontem.")
        self.rodar(mensagem(1, **ACHADO), r)
        self.assertEqual(self.consultar("SELECT data_situacao FROM item")[0][0], r.data_envio)

    def test_a_data_da_situacao_nunca_fica_no_futuro(self):
        r = resposta(2, OUTRA_PESSOA, "Oi! Acho que é minha, deixei lá ontem.", minutos=60 * 24 * 365 * 30)
        self.rodar(mensagem(1, **ACHADO), r)
        self.assertEqual(self.consultar("SELECT data_situacao <= NOW() FROM item")[0][0], True)

    def test_num_perdido_esta_comigo_de_terceiro_reivindica(self):
        self.rodar(mensagem(1, **PERDIDO), resposta(2, OUTRA_PESSOA, "Está aqui comigo, pode vir buscar no Grad 3."))
        self.assertEqual(self.item()[0], "reivindicado")

    def test_o_autor_dizendo_e_meu_nao_reivindica_o_proprio_anuncio(self):
        self.rodar(mensagem(1, **ACHADO), resposta(2, AUTORA, "Ops, na verdade é minha mesmo."))
        self.assertEqual(self.item()[0], "aberto")

    def test_mesmo_nome_com_outro_endereco_nao_e_o_autor(self):
        impostora = "Ana Lemos <fic.ana.lemos2@cin.ufpe.br>"
        self.rodar(mensagem(1, **PERDIDO), resposta(2, impostora, "Já peguei, obrigada!"))
        situacao, fonte, *_ = self.item()
        self.assertEqual((situacao, fonte), ("aberto", None))  # não é desfecho do autor

    def test_texto_citado_nao_conta(self):
        corpo = "Obrigado pelo aviso.\n\nEm qua., 1 de out. de 2026 às 09:01, Bruno escreveu:\n> é minha!"
        r = resposta(2, TERCEIRA_PESSOA, corpo)
        self.rodar(mensagem(1, **ACHADO), r)
        self.assertEqual(self.item()[0], "aberto")
        self.assertEqual(self.eventos_de_resposta(), [])
        self.assertEqual(self.repo.status_processamento(r.id_mensagem), "evento")

    # ------------------------------------------------------------ desfecho
    def test_desfecho_do_autor_encerra_a_partir_de_reivindicado(self):
        self.rodar(
            mensagem(1, **ACHADO),
            resposta(2, OUTRA_PESSOA, "É minha!"),
            resposta(3, AUTORA, "Já devolvi para o Bruno, obrigada."),
        )
        self.assertEqual(self.item()[:3], ("encerrado", "confirmação do autor", False))
        self.assertEqual(self.eventos_de_resposta()[-1][:5], ("desfecho", "confirmação do autor", True, "reivindicado", "encerrado"))

    def test_desfecho_do_autor_encerra_direto_de_aberto(self):
        self.rodar(mensagem(1, **PERDIDO), resposta(2, AUTORA, "Encontrei, pessoal. Obrigada!"))
        self.assertEqual(self.item()[:2], ("encerrado", "confirmação do autor"))

    def test_desfecho_de_terceiro_encerra_com_revisao(self):
        self.rodar(mensagem(1, **PERDIDO), resposta(2, OUTRA_PESSOA, "Foi resolvido, ela achou."))
        self.assertEqual(self.item()[:3], ("encerrado", "terceiro", True))
        self.assertEqual(self.eventos_de_resposta()[0][:3], ("desfecho", "terceiro", True))

    def test_achei_sozinho_e_ambiguo_e_nao_muda_nada(self):
        self.rodar(mensagem(1, **PERDIDO), resposta(2, AUTORA, "Achei!"))
        self.assertEqual(self.item()[0], "aberto")
        tipo, _fonte, aplicado, _ant, _nova, motivo = self.eventos_de_resposta()[0]
        self.assertEqual((tipo, aplicado), ("desfecho", False))
        self.assertIn("ambígua", motivo)

    # ------------------------------------------------------------ fora de ordem
    def test_reivindicacao_em_item_encerrado_fica_registrada_sem_mudar(self):
        self.rodar(
            mensagem(1, **PERDIDO),
            resposta(2, AUTORA, "Encontrei!! Obrigada."),
            resposta(3, OUTRA_PESSOA, "É meu esse fone, na verdade."),
        )
        self.assertEqual(self.item()[0], "encerrado")
        tipo, _f, aplicado, anterior, nova, motivo = self.eventos_de_resposta()[-1]
        self.assertEqual((tipo, aplicado, anterior, nova), ("reivindicacao", False, "encerrado", "reivindicado"))
        self.assertIn("invariante 2", motivo)

    def test_desmentido_do_autor_nao_faz_a_situacao_voltar(self):
        self.rodar(
            mensagem(1, **ACHADO),
            resposta(2, OUTRA_PESSOA, "É minha!"),
            resposta(3, AUTORA, "Bruno, não tem garrafa verde, a que achei é azul."),
        )
        self.assertEqual(self.item()[0], "reivindicado")
        tipo, _f, aplicado, _ant, nova, _m = self.eventos_de_resposta()[-1]
        self.assertEqual((tipo, aplicado, nova), ("reivindicacao", False, "aberto"))

    # ------------------------------------------------------------ piada
    def test_reivindicacao_com_risada_nao_vale(self):
        self.rodar(mensagem(1, **ACHADO), resposta(2, OUTRA_PESSOA, "é minha kkkkk"))
        self.assertEqual(self.item()[0], "aberto")
        self.assertEqual(self.eventos_de_resposta()[0][2], False)

    def test_thread_em_zoeira_nao_reivindica(self):
        self.rodar(
            mensagem(1, **ACHADO),
            resposta(2, OUTRA_PESSOA, "Que garrafa bonita", minutos=60),
            resposta(3, TERCEIRA_PESSOA, "Também quero uma", minutos=63),
            resposta(4, QUARTA_PESSOA, "A garrafa é minha", minutos=66),
        )
        self.assertEqual(self.item()[0], "aberto")

    # ------------------------------------------------------------ local e localização
    def test_correcao_de_local_pelo_autor_muda_o_local(self):
        self.rodar(mensagem(1, **PERDIDO), resposta(2, AUTORA, "Na verdade foi no Grad 4"))
        self.assertEqual(self.item()[3], ["Grad 4"])

    def test_correcao_de_local_por_terceiro_vira_so_evento(self):
        self.rodar(mensagem(1, **PERDIDO), resposta(2, OUTRA_PESSOA, "Grad 4"))
        self.assertEqual(self.item()[3], ["Grad 3"])
        tipo, fonte, aplicado, *_ = self.eventos_de_resposta()[0]
        self.assertEqual((tipo, fonte, aplicado), ("edicao", "terceiro", False))

    def test_autor_de_achado_declara_onde_o_objeto_esta(self):
        self.rodar(mensagem(1, **ACHADO), resposta(2, AUTORA, "Deixei na SecGrad, podem retirar lá."))
        _s, _f, _r, _l, localizacao, setor = self.item()
        self.assertEqual((localizacao, setor), ("com um setor", "SecGrad"))

    def test_terceiro_nunca_muda_a_localizacao(self):
        self.rodar(mensagem(1, **ACHADO), resposta(2, OUTRA_PESSOA, "Deixei na SecGrad pra ela."))
        self.assertIsNone(self.item()[4])

    # ------------------------------------------------------------ ordem e pendência
    def test_resposta_de_thread_sem_item_fica_pendente(self):
        fora = mensagem(1, assunto="[PESQUISA] Seminário", corpo="Respondam o formulário: https://docs.google.com/forms/x")
        r = resposta(2, OUTRA_PESSOA, "É minha!")
        self.rodar(fora, r)
        self.assertEqual(self.contar("item"), 0)
        self.assertIsNone(self.repo.status_processamento(r.id_mensagem))
        self.assertEqual(self.contar("evento"), 0)

    def test_uma_resposta_gera_no_maximo_um_evento_e_reprocessar_nao_duplica(self):
        mensagens = [mensagem(1, **PERDIDO), resposta(2, OUTRA_PESSOA, "Está comigo, foi resolvido.")]
        self.rodar(*mensagens)
        self.rodar(*mensagens)
        self.assertEqual(len(self.eventos_de_resposta()), 1)


class TestDecidir(unittest.TestCase):
    """Regras puras, sem banco."""

    def decidir(self, texto, remetente="b@x", tipo="achado", situacao="aberto", local=(), respostas=None):
        return decidir(tipo, situacao, list(local), None, "a@x", remetente, texto, respostas or [])

    def test_resposta_sem_sinal_nao_gera_evento(self):
        self.assertIsNone(self.decidir("Obrigado pelo aviso!"))
        self.assertIsNone(self.decidir("Obrigada a todos", remetente="a@x"))

    def test_negacao_nao_e_desfecho(self):
        self.assertIsNone(self.decidir("Ainda não encontrei, continuo procurando.", remetente="a@x", tipo="perdido"))

    def test_zoeira_exige_tres_pessoas_fora_o_autor_em_dez_minutos(self):
        from datetime import datetime, timedelta
        t0 = datetime(2026, 10, 1, 9, 0)
        tres = [RespostaAnterior(e, t0 + timedelta(minutes=m)) for e, m in [("b", 0), ("c", 4), ("d", 9)]]
        self.assertTrue(thread_virou_zoeira(tres, "a"))
        espalhadas = [RespostaAnterior(e, t0 + timedelta(minutes=m)) for e, m in [("b", 0), ("c", 8), ("d", 15)]]
        self.assertFalse(thread_virou_zoeira(espalhadas, "a"))
        com_o_autor = [RespostaAnterior(e, t0 + timedelta(minutes=m)) for e, m in [("a", 0), ("b", 1), ("c", 2)]]
        self.assertFalse(thread_virou_zoeira(com_o_autor, "a"))
