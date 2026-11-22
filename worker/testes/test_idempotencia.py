"""US-01 · idempotência (SCRUM-85).

Critérios cobertos:
- rodar o ciclo duas vezes sobre a mesma pasta não cria duplicata;
- mensagem já processada é ignorada no ciclo seguinte;
- sem mensagens novas, o ciclo encerra sem erro e sem alterar o banco;
- apagar a linha de `processamento` de uma mensagem faz reprocessar só ela, sem reler a fonte.
"""
from pathlib import Path

from worker.leitor_local import LeitorArquivoLocal
from worker.pipeline import Pipeline
from worker.testes.apoio import FonteFalsa, TesteComBanco, mensagem

CORPUS = Path("worker/corpus/casos")
TABELAS = ("mensagem_bruta", "processamento", "item", "evento", "quarentena")


class TestIdempotencia(TesteComBanco):
    def retrato(self):
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1") for t in TABELAS}

    def test_segunda_passagem_na_mesma_pasta_nao_duplica(self):
        Pipeline(self.repo).executar_ciclo(LeitorArquivoLocal(CORPUS))
        antes = self.retrato()
        resumo = Pipeline(self.repo).executar_ciclo(LeitorArquivoLocal(CORPUS))
        self.assertEqual(resumo.lidas, 70)
        self.assertEqual(resumo.novas, 0)
        self.assertEqual(self.retrato(), antes)

    def test_sem_mensagens_novas_o_ciclo_nao_altera_o_banco(self):
        m = mensagem(1, veio_da_lista=False)
        Pipeline(self.repo).executar_ciclo(FonteFalsa([m]))
        antes = self.retrato()
        resumo = Pipeline(self.repo).executar_ciclo(FonteFalsa([]))
        self.assertEqual((resumo.lidas, resumo.novas, resumo.por_status), (0, 0, {}))
        self.assertEqual(self.retrato(), antes)

    def test_mensagem_ja_processada_e_ignorada_no_ciclo_seguinte(self):
        m = mensagem(1, veio_da_lista=False)
        Pipeline(self.repo).executar_ciclo(FonteFalsa([m]))
        vistas = []

        class PipelineQueAnota(Pipeline):
            def processar_mensagem(self, msg):
                vistas.append(msg.mensagem_id)
                return super().processar_mensagem(msg)

        PipelineQueAnota(self.repo).executar_ciclo(FonteFalsa([m]))
        self.assertEqual(vistas, [])
        self.assertEqual(self.contar("processamento"), 1)

    def test_apagar_a_linha_de_processamento_reprocessa_so_aquela_mensagem(self):
        m1 = mensagem(1, thread="a", veio_da_lista=False)
        m2 = mensagem(2, thread="b", veio_da_lista=False)
        Pipeline(self.repo).executar_ciclo(FonteFalsa([m1, m2]))

        self.consultar_sem_retorno("DELETE FROM processamento WHERE mensagem_id = %s", (m1.id_mensagem,))
        vistas = []

        class PipelineQueAnota(Pipeline):
            def processar_mensagem(self, msg):
                vistas.append(msg.mensagem_id)
                return super().processar_mensagem(msg)

        # A fonte vem vazia: o reprocessamento sai de mensagem_bruta, sem reler o e-mail.
        PipelineQueAnota(self.repo).executar_ciclo(FonteFalsa([]))
        self.assertEqual(vistas, [m1.id_mensagem])
        self.assertEqual(self.repo.status_processamento(m1.id_mensagem), "ignorada")
        self.assertEqual(self.contar("mensagem_bruta"), 2)

    def consultar_sem_retorno(self, sql, parametros=()):
        with self.conexao.cursor() as cur:
            cur.execute(sql, parametros)
        self.conexao.commit()
