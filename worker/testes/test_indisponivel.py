"""US-02 · classificador indisponível não publica por omissão (SCRUM-91)."""
from worker.pipeline import Pipeline
from worker.testes.apoio import AUTORA, FonteFalsa, TesteComBanco, mensagem


class TestClassificadorIndisponivel(TesteComBanco):
    """SCRUM-91: com erro interno, nada publica e a mensagem volta no próximo ciclo."""

    def test_falha_injetada_deixa_a_mensagem_sem_processamento_e_nada_publica(self):
        def classificador_quebrado(*args, **kwargs):
            raise RuntimeError("falha injetada")

        m = mensagem(1, remetente=AUTORA, corpo="Perdi meu carregador no Grad 5.")
        with self.assertLogs("worker.pipeline", level="WARNING") as registros:
            resumo = Pipeline(self.repo, classificador=classificador_quebrado).executar_ciclo(FonteFalsa([m]))
        self.assertIn("indisponível", "\n".join(registros.output))
        self.assertNotIn("@", "\n".join(registros.output))
        self.assertEqual(resumo.pendentes, 1)
        self.assertIsNone(self.repo.status_processamento(m.id_mensagem))
        self.assertEqual((self.contar("item"), self.contar("quarentena"), self.contar("evento")), (0, 0, 0))
        self.assertEqual(self.contar("mensagem_bruta"), 1)

        # Próximo ciclo, classificador de volta: a mensagem é reavaliada a partir do bruto.
        Pipeline(self.repo).executar_ciclo(FonteFalsa([]))
        self.assertEqual(self.repo.status_processamento(m.id_mensagem), "item")
        self.assertEqual(self.contar("item"), 1)
