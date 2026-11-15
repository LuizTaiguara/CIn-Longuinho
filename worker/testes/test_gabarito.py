"""SCRUM-90 · o pipeline inteiro contra o corpus e o gabarito do PO.

Falha se `destino`, `tipo`, `situacao`, `fonte_encerramento` ou `localizacao` divergirem em
qualquer thread. `local` e `objeto` só entram no relatório (`python -m worker.avaliar`).
A `localizacao` sai das regras fechadas, não do modelo, então o teste roda com o modelo simulado.

Enquanto a US-10 (situação nas respostas, W4) não existe, `situacao`, `fonte_encerramento` e
`localizacao` são exigidos só nas threads sem resposta na lista. O W4 tira essa restrição.
"""
import unittest

from worker.avaliar import avaliar
from worker.testes.apoio import URL_TESTE, preparar_banco

ESTRITOS_SEMPRE = ["destino", "tipo"]
ESTRITOS_SEM_RESPOSTA = ["situacao", "fonte_encerramento", "localizacao"]


class TestGabarito(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        motivo = preparar_banco()
        if motivo:
            raise unittest.SkipTest(motivo)
        cls.linhas = avaliar(URL_TESTE)

    def test_cobre_todas_as_threads_do_gabarito(self):
        self.assertEqual(len(self.linhas), 32)

    def test_campos_estritos_batem_em_todas_as_threads(self):
        falhas = []
        for l in self.linhas:
            campos = ESTRITOS_SEMPRE + (ESTRITOS_SEM_RESPOSTA if l.respostas_na_lista == 0 else [])
            for campo in campos:
                if l.acertos[campo] is False:
                    falhas.append(f"caso {l.caso} ({l.thread_id}) {campo}: esperado={l.esperado.get(campo)!r} obtido={l.obtido.get(campo)!r}")
        self.assertEqual(falhas, [], "\n".join(falhas))
