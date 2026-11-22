"""US-01 · ciclo do worker (SCRUM-84).

Critérios cobertos:
- registrar cada mensagem nova com identificador, remetente, data, assunto e corpo bruto;
- mensagem_bruta gravada antes de qualquer classificação;
- só entra o que passou pela lista; o resto fica `ignorada` (decisão do PO em 13/11/2026);
- processar por thread, em ordem cronológica;
- ciclo sobre a pasta do corpus.
"""
from pathlib import Path

from worker.leitor_local import LeitorArquivoLocal
from worker.pipeline import Pipeline, agrupar_por_thread
from worker.testes.apoio import FonteFalsa, TesteComBanco, mensagem

CORPUS = Path("worker/corpus/casos")


class TestCiclo(TesteComBanco):
    def test_registra_cada_mensagem_com_identificador_remetente_data_assunto_e_corpo(self):
        m = mensagem(1, assunto="Garrafa no Grad 5", corpo="Encontrei uma garrafa azul.")
        Pipeline(self.repo).executar_ciclo(FonteFalsa([m]))

        linha = self.consultar(
            "SELECT mensagem_id, thread_id, remetente, data_envio, assunto, corpo FROM mensagem_bruta"
        )
        self.assertEqual(len(linha), 1)
        mensagem_id, thread_id, remetente, data_envio, assunto, corpo = linha[0]
        self.assertEqual(mensagem_id, "<t1.m1@teste.invalid>")
        self.assertEqual(thread_id, "t1")
        self.assertEqual(remetente, m.remetente)
        self.assertEqual(data_envio, m.data_envio)
        self.assertEqual(assunto, "Garrafa no Grad 5")
        self.assertEqual(corpo, "Encontrei uma garrafa azul.")

    def test_guarda_metadados_para_reprocessar_sem_reler_a_fonte(self):
        m = mensagem(2, em_resposta_a="<t1.m1@teste.invalid>")
        Pipeline(self.repo).executar_ciclo(FonteFalsa([m]))
        (cabecalhos,) = self.consultar("SELECT cabecalhos FROM mensagem_bruta")[0]
        self.assertTrue(cabecalhos["veio_da_lista"])
        self.assertEqual(cabecalhos["em_resposta_a"], "<t1.m1@teste.invalid>")
        self.assertEqual(cabecalhos["anexos"], [])

    def test_mensagem_de_fora_da_lista_e_gravada_e_marcada_ignorada(self):
        m = mensagem(1, veio_da_lista=False)
        resumo = Pipeline(self.repo).executar_ciclo(FonteFalsa([m]))
        self.assertEqual(self.contar("mensagem_bruta"), 1)
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "ignorada")
        self.assertEqual(resumo.por_status, {"ignorada": 1})
        self.assertEqual(self.contar("item"), 0)

    def test_mensagem_bruta_e_gravada_mesmo_se_o_processamento_quebrar(self):
        class PipelineQueQuebra(Pipeline):
            def processar_mensagem(self, mensagem):
                raise RuntimeError("falha simulada depois da gravação")

        m = mensagem(1)
        with self.assertRaises(RuntimeError):
            PipelineQueQuebra(self.repo).executar_ciclo(FonteFalsa([m]))
        self.assertEqual(self.contar("mensagem_bruta"), 1)
        self.assertEqual(self.contar("processamento"), 0)

    def test_processa_cada_thread_em_ordem_cronologica(self):
        # A fonte entrega fora de ordem; o pipeline ordena pela data de envio dentro da thread.
        fonte = FonteFalsa([
            mensagem(3, thread="b", minutos=30),
            mensagem(2, thread="a", minutos=20),
            mensagem(1, thread="a", minutos=10),
            mensagem(4, thread="b", minutos=5),
        ])
        vistas = []

        class PipelineQueAnota(Pipeline):
            def processar_mensagem(self, m):
                vistas.append(m.mensagem_id)
                return None

        PipelineQueAnota(self.repo).executar_ciclo(fonte)
        self.assertEqual(vistas.index("<a.m1@teste.invalid>") < vistas.index("<a.m2@teste.invalid>"), True)
        self.assertEqual(vistas.index("<b.m4@teste.invalid>") < vistas.index("<b.m3@teste.invalid>"), True)
        grupos = agrupar_por_thread(self.repo.mensagens_pendentes())
        self.assertEqual(list(grupos), ["b", "a"])  # threads na ordem da primeira mensagem (b começa às 9h05)

    def test_ciclo_sobre_o_corpus_grava_as_70_mensagens(self):
        resumo = Pipeline(self.repo).executar_ciclo(LeitorArquivoLocal(CORPUS))
        self.assertEqual(resumo.lidas, 70)
        self.assertEqual(self.contar("mensagem_bruta"), 70)
        # A 01 dos casos 20 e 28 e o aviso do caso 9 não passaram pela lista.
        ignoradas = self.consultar("SELECT count(*) FROM processamento WHERE status = 'ignorada'")[0][0]
        self.assertEqual(ignoradas, 3)
