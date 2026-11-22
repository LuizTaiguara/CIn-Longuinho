"""US-02 no pipeline: quarentena com motivo e publicação do que tem direção clara (SCRUM-89)."""
from worker.pipeline import Pipeline
from worker.testes.apoio import FOTO, OUTRA_PESSOA, FonteFalsa, TesteComBanco, mensagem


class TestQuarentena(TesteComBanco):
    def rodar(self, *mensagens, pipeline=None):
        return (pipeline or Pipeline(self.repo)).executar_ciclo(FonteFalsa(mensagens))

    def test_fora_de_tema_vai_para_a_quarentena_com_motivo_e_nao_vira_item(self):
        m = mensagem(1, assunto="[PESQUISA] Seminário", corpo="Respondam o formulário: https://docs.google.com/forms/x")
        self.rodar(m)
        self.assertEqual(self.contar("item"), 0)
        motivo, grau, resolvida, mensagem_id = self.consultar(
            "SELECT q.motivo_retencao, q.grau_confianca, q.resolvida, m.mensagem_id "
            "FROM quarentena q JOIN mensagem_bruta m ON m.id = q.mensagem_bruta_id"
        )[0]
        self.assertEqual((motivo, resolvida, mensagem_id), ("fora_de_tema", False, m.id_mensagem))
        self.assertIsNotNone(grau)
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "quarentena")

    def test_direcao_ambigua_vai_para_a_quarentena(self):
        self.rodar(mensagem(1, assunto="[PERDIDO]", corpo="Mouse deixado no Grad02", anexos=[FOTO]))
        self.assertEqual(self.consultar("SELECT motivo_retencao FROM quarentena")[0][0], "direcao_ambigua")
        self.assertEqual(self.contar("item"), 0)

    def test_direcao_clara_publica_mesmo_com_campos_vazios(self):
        m = mensagem(1, assunto="", corpo="Perdi meu carregador.")
        self.rodar(m)
        tipo, situacao, localizacao, origem, revisar, autor, data_anuncio = self.consultar(
            "SELECT tipo, situacao, localizacao, origem, revisar, autor_email, data_anuncio FROM item"
        )[0]
        self.assertEqual((tipo, situacao, localizacao, origem, revisar), ("perdido", "aberto", None, "lista", False))
        self.assertEqual(autor, "fic.ana.lemos@cin.ufpe.br")
        self.assertEqual(data_anuncio, m.data_envio)  # data do e-mail, não NOW()
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "item")
        tipo_evento, fonte, aplicado = self.consultar("SELECT tipo_evento, fonte, aplicado FROM evento")[0]
        self.assertEqual((tipo_evento, fonte, aplicado), ("classificacao", "detecção automática", True))

    def test_confianca_media_publica_marcada_para_revisar(self):
        self.rodar(mensagem(1, assunto="Garrafa no Grad 5", corpo="", anexos=[FOTO]))
        self.assertEqual(self.consultar("SELECT tipo, revisar FROM item")[0], ("achado", True))

    def test_confianca_baixa_retem(self):
        self.rodar(mensagem(1, assunto="Carregador encontrado", corpo="Perdi meu fone e encontrei um carregador no Grad 5."))
        self.assertEqual(self.consultar("SELECT motivo_retencao FROM quarentena")[0][0], "confianca_baixa")

    def test_algo_ja_resolvido_nasce_encerrado_pela_confirmacao_do_autor(self):
        self.rodar(mensagem(1, assunto="Retirando item esquecido",
                            corpo="Esqueci uma lousinha na sala 5, já fui buscar e tô registrando pois a portaria pediu."))
        self.assertEqual(self.consultar("SELECT situacao, fonte_encerramento FROM item")[0], ("encerrado", "confirmação do autor"))
        eventos = self.consultar("SELECT tipo_evento, situacao_nova FROM evento ORDER BY id")
        self.assertEqual(eventos, [("classificacao", "aberto"), ("edicao", None), ("desfecho", "encerrado")])

    def test_remetente_sem_endereco_publica_com_autor_vazio(self):
        self.rodar(mensagem(1, remetente="Pessoa Sem Endereço", corpo="Perdi meu carregador no Grad 5."))
        self.assertEqual(self.consultar("SELECT autor_email FROM item")[0][0], "")
        self.assertEqual(self.consultar("SELECT remetente FROM mensagem_bruta")[0][0], "Pessoa Sem Endereço")

    def test_anuncio_e_a_primeira_mensagem_da_lista_e_nao_a_primeira_da_thread(self):
        # Caso 20: a 01 foi só para a lista de alunos; o anúncio é o encaminhamento que veio depois.
        fora = mensagem(1, corpo="Perdi uma garrafa azul.", veio_da_lista=False)
        encaminhada = mensagem(2, corpo="Perdi uma garrafa azul.", em_resposta_a=fora.id_mensagem)
        self.rodar(fora, encaminhada)
        self.assertEqual(self.contar("item"), 1)
        self.assertEqual(self.repo.status_processamento(fora.id_mensagem), "ignorada")
        self.assertEqual(self.repo.status_processamento(encaminhada.id_mensagem), "item")

    def test_resposta_nao_e_classificada_como_anuncio(self):
        anuncio = mensagem(1, corpo="Encontrei uma garrafa azul no Grad 5.")
        resposta = mensagem(2, remetente=OUTRA_PESSOA, assunto="Re: Garrafa", corpo="Perdi uma garrafa ontem!")
        self.rodar(anuncio, resposta)
        self.assertEqual(self.contar("item"), 1)
        self.assertEqual(self.consultar("SELECT tipo FROM item")[0][0], "achado")

