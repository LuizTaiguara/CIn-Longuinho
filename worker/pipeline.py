"""Um ciclo do worker: ler → gravar mensagem_bruta → processar o que está pendente.

O ciclo tem duas fases, e a separação é o que garante as regras da US-01:

1. **Ingestão.** Cada mensagem da fonte é gravada em `mensagem_bruta` antes de qualquer outra coisa.
   Se o resto quebrar, o bruto já está salvo. Mensagem repetida não duplica (Message-ID único).
2. **Processamento.** O pipeline pega do banco as mensagens sem linha em `processamento`, agrupa por
   thread e processa em ordem cronológica. Por isso reprocessar é só apagar a linha de
   `processamento`: a mensagem volta a ser pendente e o worker não precisa reler a fonte.

Cada mensagem é processada numa transação própria, que termina com a linha de `processamento`.
Se algo falha no meio, a transação volta e a mensagem continua pendente para o próximo ciclo.
"""
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from worker.banco import MensagemBruta, Repositorio
from worker.fonte import FonteMensagens

log = logging.getLogger("worker.pipeline")


@dataclass
class ResumoCiclo:
    """O que um ciclo fez. Só contagens: nada de remetente nem de texto (invariante 1)."""

    lidas: int = 0
    novas: int = 0
    por_status: Dict[str, int] = field(default_factory=dict)
    pendentes: int = 0

    def contar(self, status: Optional[str]) -> None:
        if status is None:
            self.pendentes += 1
        else:
            self.por_status[status] = self.por_status.get(status, 0) + 1

    def __str__(self) -> str:
        status = ", ".join(f"{k}={v}" for k, v in sorted(self.por_status.items())) or "nenhuma"
        return (
            f"lidas={self.lidas} novas={self.novas} processadas: {status}; "
            f"aguardando próximo ciclo={self.pendentes}"
        )


def agrupar_por_thread(mensagens: List[MensagemBruta]) -> "OrderedDict[str, List[MensagemBruta]]":
    """Agrupa mantendo a ordem cronológica dentro de cada thread."""
    grupos: "OrderedDict[str, List[MensagemBruta]]" = OrderedDict()
    for m in mensagens:
        grupos.setdefault(m.thread_id, []).append(m)
    for lista in grupos.values():
        lista.sort(key=lambda m: (m.data_envio is None, m.data_envio, m.id))
    return grupos


class Pipeline:
    def __init__(self, repositorio: Repositorio):
        self.repo = repositorio

    # ------------------------------------------------------------------ fase 1
    def ingerir(self, fonte: FonteMensagens, resumo: ResumoCiclo) -> None:
        """Grava em `mensagem_bruta` tudo o que a fonte entregar. Exceções da fonte sobem."""
        for msg in fonte.obter_mensagens():
            resumo.lidas += 1
            if self.repo.gravar_mensagem_bruta(msg):
                resumo.novas += 1

    # ------------------------------------------------------------------ fase 2
    def processar_pendentes(self, resumo: ResumoCiclo) -> None:
        pendentes = self.repo.mensagens_pendentes()
        for _thread_id, mensagens in agrupar_por_thread(pendentes).items():
            for mensagem in mensagens:
                status = self._processar_em_transacao(mensagem)
                resumo.contar(status)

    def _processar_em_transacao(self, mensagem: MensagemBruta) -> Optional[str]:
        conexao = self.repo.conexao
        try:
            status = self.processar_mensagem(mensagem)
            if status is not None:
                self.repo.marcar_processamento(mensagem, status)
            conexao.commit()
            return status
        except Exception:
            conexao.rollback()
            raise

    def processar_mensagem(self, mensagem: MensagemBruta) -> Optional[str]:
        """Decide o destino de uma mensagem. Devolve o `processamento.status` ou None (fica pendente).

        Só entra no catálogo o que passou por achados-perdidos@cin.ufpe.br (decisão do PO em
        13/11/2026). O resto é gravado e marcado `ignorada`. As mensagens da lista ficam pendentes
        até existir o classificador (US-02).
        """
        if not mensagem.veio_da_lista:
            return "ignorada"
        return None

    # ------------------------------------------------------------------ ciclo
    def executar_ciclo(self, fonte: FonteMensagens) -> ResumoCiclo:
        resumo = ResumoCiclo()
        self.ingerir(fonte, resumo)
        self.processar_pendentes(resumo)
        return resumo
