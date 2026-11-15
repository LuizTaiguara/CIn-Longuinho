"""US-07 (ligação pelo código, SCRUM-56) e US-15 (aviso ao autor, SCRUM-106)."""
import unittest
from datetime import datetime, timezone

from worker.aviso import ConfigAviso
from worker.envio import EnvioIndisponivel, NaoEnviar, ParaArquivo, criar_envio
from worker.pipeline import Pipeline
from worker.testes.apoio import AUTORA, LISTA, OUTRA_PESSOA, FonteFalsa, TesteComBanco, mensagem

CODIGO = "AP-K7M2QX"
SITE = "https://achados.exemplo.invalid"
DESDE_SEMPRE = ConfigAviso(site_url=SITE, a_partir_de=datetime(2000, 1, 1, tzinfo=timezone.utc))


class EnvioQueFalha(NaoEnviar):
    def _entregar(self, msg):
        raise EnvioIndisponivel("SMTP fora")


class TestLigacaoPorCodigo(TesteComBanco):
    def setUp(self):
        super().setUp()
        self.item_id = self.consultar(
            "INSERT INTO item (codigo, tipo, descricao, autor_email, origem) "
            "VALUES (%s, 'perdido', 'Fone preto', 'fic.ana.lemos@cin.ufpe.br', 'site') RETURNING id",
            (CODIGO,),
        )[0][0]

    def rodar(self, *mensagens):
        return Pipeline(self.repo, envio=NaoEnviar(), config_aviso=DESDE_SEMPRE).executar_ciclo(FonteFalsa(mensagens))

    def test_codigo_no_assunto_liga_a_thread_sem_classificar_nem_criar_item(self):
        m = mensagem(1, thread="t9", assunto=f"[{CODIGO}] Perdi meu fone preto", corpo="Perdi meu fone preto no Grad 3.")
        self.rodar(m)
        self.assertEqual(self.contar("item"), 1)
        thread_id, origem = self.consultar("SELECT thread_id, origem FROM item")[0]
        self.assertEqual((thread_id, origem), ("t9", "site"))
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "ligada")
        eventos = self.consultar("SELECT tipo_evento, aplicado, detalhes->>'codigo' FROM evento")
        self.assertEqual(eventos, [("ligacao_thread", True, CODIGO)])

    def test_codigo_no_corpo_tambem_liga(self):
        self.rodar(mensagem(1, thread="t9", assunto="Fone preto", corpo=f"Perdi meu fone.\n\nCódigo do catálogo: [{CODIGO}]"))
        self.assertEqual(self.consultar("SELECT thread_id FROM item")[0][0], "t9")

    def test_respostas_da_thread_ligada_mudam_a_situacao_do_item_do_site(self):
        self.rodar(
            mensagem(1, thread="t9", assunto=f"[{CODIGO}] Perdi meu fone", corpo="Perdi meu fone."),
            mensagem(2, thread="t9", remetente=OUTRA_PESSOA, assunto=f"Re: [{CODIGO}] Perdi meu fone",
                     corpo="Está aqui comigo na SecGrad.", minutos=40),
        )
        self.assertEqual(self.consultar("SELECT situacao FROM item")[0][0], "reivindicado")

    def test_segunda_thread_com_o_mesmo_codigo_fica_so_no_historico(self):
        self.rodar(
            mensagem(1, thread="t9", assunto=f"[{CODIGO}] Perdi meu fone", corpo="Perdi meu fone."),
            mensagem(1, thread="t10", assunto=f"[{CODIGO}] Perdi meu fone", corpo="Perdi meu fone.", minutos=90),
        )
        self.assertEqual(self.contar("item"), 1)
        self.assertEqual(self.consultar("SELECT thread_id FROM item")[0][0], "t9")
        eventos = self.consultar("SELECT aplicado, motivo_recusa IS NOT NULL FROM evento WHERE tipo_evento = 'ligacao_thread' ORDER BY id")
        self.assertEqual(eventos, [(True, False), (False, True)])

    def test_codigo_desconhecido_segue_o_fluxo_normal(self):
        self.rodar(mensagem(1, thread="t9", assunto="[AP-ZZZZZZ] Perdi meu fone", corpo="Perdi meu fone preto."))
        self.assertEqual(self.contar("item"), 2)
        self.assertEqual(self.consultar("SELECT origem FROM item WHERE thread_id = 't9'")[0][0], "lista")

    def test_reprocessar_a_mensagem_ligada_nao_duplica_o_evento(self):
        m = mensagem(1, thread="t9", assunto=f"[{CODIGO}] Perdi meu fone", corpo="Perdi meu fone.")
        self.rodar(m)
        self.consultar("DELETE FROM processamento RETURNING 1")
        self.rodar(m)
        self.assertEqual(self.contar("evento"), 1)
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "ligada")


class TestAvisoAoAutor(TesteComBanco):
    def rodar(self, *mensagens, envio=None, config=DESDE_SEMPRE):
        self.envio = envio or NaoEnviar("projeto@exemplo.invalid")
        return Pipeline(self.repo, envio=self.envio, config_aviso=config).executar_ciclo(FonteFalsa(mensagens))

    def test_envia_um_aviso_ao_autor_com_o_link_do_item(self):
        self.rodar(mensagem(1))
        item_id, enviado_em = self.consultar("SELECT id, aviso_autor_enviado_em FROM item")[0]
        self.assertIsNotNone(enviado_em)
        [msg] = self.envio.enviados
        self.assertEqual(msg["To"], "fic.ana.lemos@cin.ufpe.br")
        corpo = msg.get_content()
        self.assertIn(f"{SITE}/itens/item_{item_id}", corpo)
        self.assertIn("conta do CIn", corpo)
        self.assertNotIn("token", corpo.lower())
        self.assertEqual(self.consultar("SELECT aplicado FROM evento WHERE tipo_evento = 'aviso_autor'"), [(True,)])

    def test_nunca_vai_para_a_lista(self):
        from_lista = mensagem(1, remetente=f"Lista <{LISTA}>")
        self.rodar(from_lista, mensagem(1, thread="t2", minutos=5))
        destinatarios = [m["To"].lower() for m in self.envio.enviados]
        self.assertNotIn(LISTA, " ".join(destinatarios))
        self.assertEqual(destinatarios, ["fic.ana.lemos@cin.ufpe.br"])
        recusa = self.consultar(
            "SELECT e.aplicado FROM evento e JOIN item i ON i.id = e.item_id "
            "WHERE i.thread_id = 't1' AND e.tipo_evento = 'aviso_autor'"
        )
        self.assertEqual(recusa, [(False,)])

    def test_nunca_envia_duas_vezes_para_a_mesma_thread(self):
        m = mensagem(1)
        resposta = mensagem(2, remetente=OUTRA_PESSOA, assunto="Re: Garrafa no Grad 5", corpo="Obrigado!", minutos=40)
        self.rodar(m, resposta)
        envio = self.envio
        Pipeline(self.repo, envio=envio, config_aviso=DESDE_SEMPRE).executar_ciclo(FonteFalsa([m, resposta]))
        self.consultar("DELETE FROM processamento RETURNING 1")  # reprocessar tudo também não reenvia
        Pipeline(self.repo, envio=envio, config_aviso=DESDE_SEMPRE).executar_ciclo(FonteFalsa([m, resposta]))
        self.assertEqual(len(envio.enviados), 1)
        self.assertEqual(self.contar("evento WHERE tipo_evento = 'aviso_autor'"), 1)

    def test_item_sem_autor_email_nao_recebe_aviso(self):
        self.rodar(mensagem(1, remetente="Remetente sem endereço"))
        self.assertEqual(self.envio.enviados, [])

    def test_falha_no_envio_deixa_o_aviso_para_o_proximo_ciclo(self):
        self.rodar(mensagem(1), envio=EnvioQueFalha())
        self.assertIsNone(self.consultar("SELECT aviso_autor_enviado_em FROM item")[0][0])
        self.assertEqual(self.contar("evento WHERE tipo_evento = 'aviso_autor'"), 0)
        self.rodar(mensagem(1))
        self.assertEqual(len(self.envio.enviados), 1)

    def test_sem_data_de_inicio_nenhum_aviso_sai(self):
        self.rodar(mensagem(1), config=ConfigAviso(site_url=SITE, a_partir_de=None))
        self.assertEqual(self.envio.enviados, [])

    def test_anuncio_anterior_a_data_de_inicio_nao_recebe_aviso(self):
        self.rodar(mensagem(1), config=ConfigAviso(site_url=SITE, a_partir_de=datetime(2027, 1, 1, tzinfo=timezone.utc)))
        self.assertEqual(self.envio.enviados, [])

    def test_item_que_ja_nasce_encerrado_nao_recebe_aviso(self):
        self.rodar(mensagem(1, assunto="Garrafa", corpo="Esqueci minha garrafa no Grad 5, mas já fui buscar. Só registrando."))
        self.assertEqual(self.consultar("SELECT situacao FROM item")[0][0], "encerrado")
        self.assertEqual(self.envio.enviados, [])


class TestEnvio(unittest.TestCase):
    def test_modo_arquivo_grava_eml(self):
        import tempfile
        from pathlib import Path
        from worker.envio import EmailSaida
        with tempfile.TemporaryDirectory() as pasta:
            ParaArquivo("projeto@exemplo.invalid", pasta).enviar(EmailSaida("fic.ana.lemos@cin.ufpe.br", "Assunto", "Corpo"))
            [arquivo] = list(Path(pasta).glob("*.eml"))
            self.assertIn(b"To: fic.ana.lemos@cin.ufpe.br", arquivo.read_bytes())

    def test_smtp_sem_credencial_recusa_configurar(self):
        with self.assertRaises(ValueError):
            criar_envio({"EMAIL_MODO_ENVIO": "smtp"})

    def test_modo_padrao_nao_envia(self):
        self.assertIsInstance(criar_envio({}), NaoEnviar)
