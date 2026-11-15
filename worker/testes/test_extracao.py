"""US-03 · extração (SCRUM-92 GLiNER, SCRUM-93 campo vazio, SCRUM-94 vários objetos num item).

Os testes usam um modelo falso que devolve entidades fixas, no formato do GLiNER. O teste com o
modelo de verdade só roda com WORKER_TESTE_GLINER=1 (precisa do modelo em cache ou de rede).
"""
import os
import unittest

from worker.extrator import (
    ModeloGliner,
    ModeloIndisponivel,
    descricao_do_assunto,
    enumerar,
    extrair,
    localizacao_declarada,
    locais_por_regra,
    normalizar_local,
)
from worker.pipeline import Pipeline
from worker.testes.apoio import FOTO, FonteFalsa, TesteComBanco, mensagem


class ModeloFalso:
    """Devolve as entidades combinadas, só as que aparecem no texto (como o GLiNER)."""

    def __init__(self, **por_rotulo):
        self.por_rotulo = por_rotulo
        self.chamadas = 0

    def __call__(self, texto, rotulos):
        self.chamadas += 1
        return [
            {"label": rotulo, "text": trecho, "score": 0.9}
            for rotulo, trechos in self.por_rotulo.items()
            for trecho in trechos
            if trecho.lower() in texto.lower()
        ]


class ModeloFora:
    def __call__(self, texto, rotulos):
        raise ModeloIndisponivel("sem rede e sem cache")


class TestRegrasDeLocal(unittest.TestCase):
    """O dicionário de apelidos da tabela `local`."""

    def test_apelidos_das_grads_viram_o_nome_oficial(self):
        for apelido in ["Grad05", "grad 5", "Grad 05", "GRAD5", "grad5"]:
            self.assertEqual(normalizar_local(apelido), "Grad 5", apelido)
        self.assertEqual(normalizar_local("Grad02"), "Grad 2")

    def test_laboratorio_de_hardware_inclusive_com_erro_de_digitacao(self):
        for apelido in ["lab de hardware", "laboratório de hardware", "laboratorio de harware"]:
            self.assertEqual(normalizar_local(apelido), "Laboratório de hardware", apelido)

    def test_sala_no_formato_do_cin(self):
        self.assertEqual(normalizar_local("e132"), "E132")
        self.assertEqual(locais_por_regra("na sala E132, no Grad 5 ou no Grad 1"), ["Grad 1", "Grad 5", "E132"])

    def test_o_que_nao_e_reconhecido_fica_como_texto_livre(self):
        self.assertEqual(normalizar_local("banheiro masculino do 2º andar do bloco E"), "banheiro masculino do 2º andar do bloco E")


class TestLocalizacaoDeclarada(unittest.TestCase):
    """Invariante 3: só frase explícita, de uma lista fechada."""

    def test_padroes_aceitos(self):
        casos = {
            "O item se encontra no local.": ("no local", None),  # caso 2
            "Deixei lá mesmo, em cima da mesa.": ("no local", None),
            "Guardei na minha carteira, por favor entrar em contato.": ("com quem achou", None),  # caso 6
            "Levei um casaco para casa achando que era o meu.": ("com quem achou", None),  # caso 12
            "Está comigo, me chamem.": ("com quem achou", None),
            "Por favor, dono do fone, entre em contato comigo para eu lhe entregar": ("com quem achou", None),  # caso 21
            "Para retirada na Secretaria de Graduação (sala E124).": ("com um setor", "SecGrad"),  # caso 16
            "Deixei na secgrad.": ("com um setor", "SecGrad"),
            "Entreguei na Gerinfra.": ("com um setor", "Gerinfra"),
            "Deixei com o professor Ricardo.": ("com um setor", "professor Ricardo"),
        }
        for frase, esperado in casos.items():
            self.assertEqual(localizacao_declarada(frase), esperado, frase)

    def test_nada_fora_da_lista_preenche(self):
        for frase in [
            "vou deixar na portaria do bloco A",  # caso 14: a portaria não guarda objetos
            "Deixei na portaria do bloco E.",  # caso 15
            "Esse aparelho encontra-se na recepção do Bloco E.",
            "tudo aí está na sala E112 e continua lá",  # caso 5
            "Fone deixado em uma das mesas do Mezanino",
            "Encontrei esse carregador no Grad 5",
            "Se alguém achou, entre em contato comigo",
        ]:
            self.assertEqual(localizacao_declarada(frase), (None, None), frase)

    def test_localizacao_so_vale_para_achado(self):
        modelo = ModeloFalso()
        r = extrair("Fone", "Perdi meu fone. Acho que ficou lá no Grad 5.", "perdido", modelo)
        self.assertIsNone(r.localizacao)


class TestExtrair(unittest.TestCase):
    def test_preenche_o_que_o_modelo_marcou_e_normaliza_o_local(self):
        modelo = ModeloFalso(objeto=["óculos escuros"], local=["grad5"], data=["hoje"])
        r = extrair("[PERDIDO] Óculos escuros dourado", "Encontrado no grad5 do lado do G5C53", "achado", modelo)
        self.assertEqual(r.objetos, ["óculos escuros"])
        self.assertEqual(r.locais, ["Grad 5"])
        # O assunto nomeia o objeto e é curto: vira a descrição, sem a etiqueta.
        self.assertEqual(r.descricao, "Óculos escuros dourado")
        self.assertIsNone(r.localizacao)

    def test_descricao_do_assunto_tira_direcao_e_local(self):
        self.assertEqual(descricao_do_assunto("Batom perdido no grad 4", ["batom"]), "Batom")
        self.assertEqual(descricao_do_assunto("Mouse Preto Logitech G305", ["mouse"]), "Mouse Preto Logitech G305")
        # Frase, assunto em maiúsculas ou assunto que não nomeia o objeto: usa os objetos.
        self.assertIsNone(descricao_do_assunto("Perdi uma garrafa no Grad 5", ["garrafa"]))
        self.assertIsNone(descricao_do_assunto("CELULAR PERDIDO", ["celular"]))
        self.assertIsNone(descricao_do_assunto("Ajuda!", ["garrafa"]))

    def test_pronome_ou_pedaco_de_frase_nao_vira_objeto(self):
        modelo = ModeloFalso(objeto=["celular", "Esse aparelho", "disponível para retirada"])
        r = extrair("CELULAR", "Achei um celular. Esse aparelho está disponível para retirada.", "achado", modelo)
        self.assertEqual(r.objetos, ["celular"])

    def test_campo_nao_identificado_fica_vazio_e_nada_e_inventado(self):
        r = extrair("Mouse", "Hoje acabei esquecendo o meu mouse.", "perdido", ModeloFalso())
        self.assertEqual((r.objetos, r.locais, r.datas, r.localizacao, r.setor), ([], [], [], None, None))
        self.assertEqual(r.descricao, "Mouse")  # sem objeto extraído, o assunto limpo

    def test_varios_objetos_ficam_num_item_e_a_descricao_preserva_a_enumeracao(self):
        modelo = ModeloFalso(objeto=["Boné bege NY", "garrafa d'água preta"], local=["sala E132"])
        r = extrair("[PERDIDO] Boné bege NY e garrafa d'água preta", "Foi achado agora na sala E132", "achado", modelo)
        self.assertEqual(r.descricao, "Boné bege NY e garrafa d'água preta")
        self.assertEqual(r.locais, ["E132"])
        self.assertEqual(enumerar(["a", "b", "c"]), "A, b e c")

    def test_contato_nao_vai_para_os_detalhes(self):
        modelo = ModeloFalso(contato=["fic.rui.cardim@cin.ufpe.br"], objeto=["casaco"])
        r = extrair("Casaco", "Levei um casaco para casa. Contato: fic.rui.cardim@cin.ufpe.br", "achado", modelo)
        self.assertTrue(r.tem_contato)
        self.assertNotIn("@", str(r.detalhes()))

    def test_nome_de_pessoa_sai_da_descricao_publica(self):
        # Caso 14: o crachá traz o nome de um terceiro.
        modelo = ModeloFalso(objeto=["crachá de Heitor Sampaio"], pessoa=["Heitor Sampaio"])
        r = extrair("Crachá perdido no Grad02", "Encontrei o crachá de Heitor Sampaio no grad 02", "achado", modelo)
        self.assertEqual(r.descricao, "Crachá")
        self.assertNotIn("Heitor", str(r.detalhes()))

    def test_erro_de_digitacao_nao_derruba(self):
        # Caso 29: sem assunto, "harware", "fsbor".
        r = extrair("", "Perdi o carregador com entrada ligntning no laboratorio de harware, por fsbor entrar em contato",
                    "perdido", ModeloFalso(objeto=["carregador"]))
        self.assertEqual(r.locais, ["Laboratório de hardware"])
        self.assertEqual(r.descricao, "Carregador")

    def test_modelo_inexistente_sem_rede_vira_modelo_indisponivel(self):
        antes = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            with self.assertRaises(ModeloIndisponivel):
                ModeloGliner("inexistente/modelo-que-nao-existe")("texto", ["objeto"])
        finally:
            if antes is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = antes


class TestExtracaoNoPipeline(TesteComBanco):
    def test_item_publica_com_os_campos_extraidos_e_um_evento_extracao(self):
        modelo = ModeloFalso(objeto=["bolsa"], local=["banheiro masculino do 2° andar do bloco E"])
        m = mensagem(1, assunto="Bolsa perdida",
                     corpo="Tem uma bolsa perdida no reservado do banheiro masculino do 2° andar do bloco E. O item se encontra no local.")
        Pipeline(self.repo, modelo_extracao=modelo).executar_ciclo(FonteFalsa([m]))
        descricao, local, localizacao = self.consultar("SELECT descricao, local, localizacao FROM item")[0]
        self.assertEqual(descricao, "Bolsa")
        self.assertEqual(local, ["banheiro masculino do 2° andar do bloco E"])
        self.assertEqual(localizacao, "no local")
        aplicado, detalhes = self.consultar("SELECT aplicado, detalhes FROM evento WHERE tipo_evento = 'extracao'")[0]
        self.assertTrue(aplicado)
        self.assertEqual(detalhes["objetos"], ["bolsa"])

    def test_modelo_indisponivel_publica_so_com_a_classificacao_e_e_reprocessavel(self):
        m = mensagem(1, assunto="Carregador", corpo="Encontrei um carregador no Grad 05.")
        Pipeline(self.repo, modelo_extracao=ModeloFora()).executar_ciclo(FonteFalsa([m]))
        tipo, descricao, local = self.consultar("SELECT tipo, descricao, local FROM item")[0]
        self.assertEqual((tipo, descricao, local), ("achado", "Carregador", []))
        aplicado, motivo = self.consultar("SELECT aplicado, motivo_recusa FROM evento WHERE tipo_evento = 'extracao'")[0]
        self.assertFalse(aplicado)
        self.assertIn("reprocessável", motivo)

        # Reprocessar: apagar a linha de processamento. Volta o modelo; só a extração roda.
        self.consultar_sem_retorno("DELETE FROM processamento WHERE mensagem_id = %s", (m.id_mensagem,))
        Pipeline(self.repo, modelo_extracao=ModeloFalso(objeto=["carregador"])).executar_ciclo(FonteFalsa([]))
        self.assertEqual(self.contar("item"), 1)
        self.assertEqual(self.consultar("SELECT descricao, local FROM item")[0], ("Carregador", ["Grad 5"]))
        self.assertEqual(self.contar("quarentena"), 0)

    def test_reextracao_depois_da_classificacao_pelo_autor_preenche_so_o_vazio(self):
        # Caso 11: retida por direção ambígua; o autor diz em "Meus anúncios" que é um perdido.
        m = mensagem(1, assunto="[PERDIDO]", corpo="Mouse deixado no Grad02", anexos=[FOTO])
        modelo = ModeloFalso(objeto=["Mouse"], local=["Grad02"])
        Pipeline(self.repo, modelo_extracao=modelo).executar_ciclo(FonteFalsa([m]))
        self.assertEqual(self.contar("item"), 0)

        self.simular_classificacao_pela_api(m, tipo="perdido")
        Pipeline(self.repo, modelo_extracao=modelo).executar_ciclo(FonteFalsa([]))

        tipo, situacao, descricao, local, localizacao = self.consultar(
            "SELECT tipo, situacao, descricao, local, localizacao FROM item")[0]
        self.assertEqual((tipo, situacao), ("perdido", "aberto"))  # nunca muda tipo nem situação
        self.assertEqual(descricao, "Mouse")
        self.assertEqual(local, ["Grad 2"])
        self.assertIsNone(localizacao)
        eventos = [e for (e,) in self.consultar("SELECT tipo_evento FROM evento ORDER BY id")]
        self.assertEqual(eventos, ["classificacao_pelo_autor", "extracao"])
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "item")

    def test_reextracao_nao_sobrescreve_o_que_o_autor_ja_preencheu(self):
        m = mensagem(1, assunto="Carregador", corpo="Encontrei um carregador no Grad 05.")
        Pipeline(self.repo, modelo_extracao=ModeloFora()).executar_ciclo(FonteFalsa([m]))
        self.consultar_sem_retorno("UPDATE item SET descricao = 'Carregador USB-C branco', local = ARRAY['Grad 4']")
        self.consultar_sem_retorno("DELETE FROM processamento WHERE mensagem_id = %s", (m.id_mensagem,))
        Pipeline(self.repo, modelo_extracao=ModeloFalso(objeto=["carregador"])).executar_ciclo(FonteFalsa([]))
        self.assertEqual(self.consultar("SELECT descricao, local FROM item")[0], ("Carregador USB-C branco", ["Grad 4"]))

    # ------------------------------------------------------------------ apoio
    def consultar_sem_retorno(self, sql, parametros=()):
        with self.conexao.cursor() as cur:
            cur.execute(sql, parametros)
        self.conexao.commit()

    def simular_classificacao_pela_api(self, m, tipo):
        """O que `POST /eu/retidas/{id}/classificar` faz no banco (metaprompt da API)."""
        with self.conexao.cursor() as cur:
            cur.execute("SELECT id FROM mensagem_bruta WHERE mensagem_id = %s", (m.id_mensagem,))
            (bruta_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO item (thread_id, tipo, descricao, autor_email, origem, data_anuncio) "
                "VALUES (%s, %s, '', 'fic.ana.lemos@cin.ufpe.br', 'lista', %s) RETURNING id",
                (m.id_conversa, tipo, m.data_envio),
            )
            (item_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO evento (item_id, tipo_evento, fonte, aplicado) "
                "VALUES (%s, 'classificacao_pelo_autor', 'classificação pelo autor', TRUE)",
                (item_id,),
            )
            cur.execute("UPDATE quarentena SET resolvida = TRUE WHERE mensagem_bruta_id = %s", (bruta_id,))
            cur.execute("DELETE FROM processamento WHERE mensagem_id = %s", (m.id_mensagem,))
        self.conexao.commit()


@unittest.skipUnless(os.environ.get("WORKER_TESTE_GLINER") == "1", "modelo real só com WORKER_TESTE_GLINER=1")
class TestGlinerDeVerdade(unittest.TestCase):
    """Com o GLiNER de verdade (em cache): caso 3, dois objetos num anúncio."""

    @classmethod
    def setUpClass(cls):
        cls.modelo = ModeloGliner()

    def test_caso3_extrai_os_dois_objetos_e_a_sala(self):
        r = extrair("[PERDIDO] Boné bege NY e garrafa d'água preta",
                    "Foi achado agora (21/10 às 14:30) na sala E132", "achado", self.modelo)
        texto = (r.descricao or "").lower()
        self.assertIn("boné", texto)
        self.assertIn("garrafa", texto)
        self.assertIn("E132", r.locais)
