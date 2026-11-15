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
from typing import Callable, Dict, List, Optional

from worker.banco import MensagemBruta, Repositorio
from worker.classificador import Classificacao, classificar
from worker.fonte import FonteMensagens
from worker.texto import limpar_assunto, limpar_corpo

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


FONTE_AUTOMATICA = "detecção automática"
FONTE_AUTOR = "confirmação do autor"


def primeira_da_lista(mensagens: List[MensagemBruta]) -> Optional[MensagemBruta]:
    """O anúncio da thread: a primeira mensagem, em ordem de envio, que passou pela lista."""
    for m in sorted(mensagens, key=lambda m: (m.data_envio is None, m.data_envio, m.id)):
        if m.veio_da_lista:
            return m
    return None


def tem_imagem(mensagem: MensagemBruta) -> bool:
    return any(str(a.get("tipo_mime", "")).startswith("image/") for a in mensagem.anexos)


def descricao_inicial(mensagem: MensagemBruta, corpo_limpo: str) -> Optional[str]:
    """Descrição antes da extração: o assunto sem etiquetas; sem assunto, o começo do corpo."""
    assunto = limpar_assunto(mensagem.assunto)
    if assunto:
        return assunto
    primeira_linha = " ".join(corpo_limpo.split())
    return primeira_linha[:140] or None


class Pipeline:
    def __init__(self, repositorio: Repositorio, classificador: Callable[..., Classificacao] = classificar):
        self.repo = repositorio
        self.classificar = classificador

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
        13/11/2026). O resto é gravado e marcado `ignorada`. A primeira mensagem da thread que passou
        pela lista é o anúncio; as seguintes são respostas.
        """
        if not mensagem.veio_da_lista:
            return "ignorada"
        thread = self.repo.mensagens_da_thread(mensagem.thread_id)
        anuncio = primeira_da_lista(thread)
        if anuncio is not None and anuncio.mensagem_id == mensagem.mensagem_id:
            return self.processar_anuncio(mensagem, thread)
        return self.processar_resposta(mensagem, anuncio)

    def processar_anuncio(self, mensagem: MensagemBruta, thread: List[MensagemBruta]) -> Optional[str]:
        if self.repo.item_da_thread(mensagem.thread_id) is not None:
            return "item"

        ids_da_thread = {m.mensagem_id for m in thread}
        thread_incompleta = bool(mensagem.em_resposta_a) and mensagem.em_resposta_a not in ids_da_thread
        corpo = limpar_corpo(mensagem.corpo)
        try:
            classificacao = self.classificar(mensagem.assunto, corpo, tem_imagem(mensagem), thread_incompleta)
        except Exception as erro:  # SCRUM-91: nada publica por omissão; volta no próximo ciclo
            log.warning(
                "classificador indisponível para a mensagem_bruta %s; fica pendente (%s)", mensagem.id, type(erro).__name__
            )
            return None

        if classificacao.destino == "quarentena":
            self.repo.reter(mensagem, classificacao.motivo_retencao, classificacao.confianca)
            return "quarentena"

        item_id = self.repo.criar_item(
            thread_id=mensagem.thread_id,
            tipo=classificacao.tipo,
            descricao=descricao_inicial(mensagem, corpo),
            autor_email=mensagem.email_remetente,
            data_anuncio=mensagem.data_envio,
            revisar=classificacao.revisar,
        )
        self.repo.registrar_evento(
            item_id, "classificacao", FONTE_AUTOMATICA, True,
            situacao_nova="aberto", detalhes=classificacao.detalhes(),
        )
        if classificacao.ja_encerrado:
            # Caso 8: "esqueci, já fui buscar, estou registrando". Nasce encerrado pelo próprio autor.
            self.repo.mudar_situacao(item_id, "encerrado", fonte_encerramento=FONTE_AUTOR)
            self.repo.registrar_evento(
                item_id, "desfecho", FONTE_AUTOR, True,
                situacao_anterior="aberto", situacao_nova="encerrado",
                detalhes={"regra": "anuncio_de_algo_ja_resolvido"},
            )
        return "item"

    def processar_resposta(self, mensagem: MensagemBruta, anuncio: Optional[MensagemBruta]) -> Optional[str]:
        """Respostas ficam pendentes até a US-10 (situação na thread) ser implementada."""
        return None

    # ------------------------------------------------------------------ ciclo
    def executar_ciclo(self, fonte: FonteMensagens) -> ResumoCiclo:
        resumo = ResumoCiclo()
        self.ingerir(fonte, resumo)
        self.processar_pendentes(resumo)
        return resumo
