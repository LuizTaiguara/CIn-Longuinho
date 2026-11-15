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
from worker.situacao import RespostaAnterior, decidir
from worker.extrator import Extracao, ModeloIndisponivel, criar_modelo, extrair
from worker.fonte import FonteMensagens
from worker.texto import limpar_assunto, limpar_corpo

# `evento.tipo_evento` só aceita o vocabulário de shared/AGENTS.md: a extração entra como `edicao`
# (ela preenche campos do item) e a regra nos detalhes diz de onde veio.
REGRA_EXTRACAO = "extracao_automatica"

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
    def __init__(
        self,
        repositorio: Repositorio,
        classificador: Callable[..., Classificacao] = classificar,
        modelo_extracao: Optional[Callable] = None,
    ):
        self.repo = repositorio
        self.classificar = classificador
        self.modelo = modelo_extracao if modelo_extracao is not None else criar_modelo()

    def _extrair(self, mensagem: MensagemBruta, corpo: str, tipo: str):
        """Devolve (Extracao, None) ou (None, motivo) se o modelo estiver indisponível."""
        try:
            return extrair(mensagem.assunto, corpo, tipo, self.modelo), None
        except ModeloIndisponivel as erro:
            log.warning("extração indisponível para a mensagem_bruta %s: %s", mensagem.id, erro)
            return None, str(erro)

    def _registrar_extracao(self, item_id: int, extracao: Optional[Extracao], motivo: Optional[str], campos=None) -> None:
        if extracao is None:
            self.repo.registrar_evento(
                item_id, "edicao", FONTE_AUTOMATICA, False,
                motivo_recusa=f"modelo de extração indisponível; item reprocessável ({motivo})",
                detalhes={"regra": REGRA_EXTRACAO},
            )
            return
        detalhes = {"regra": REGRA_EXTRACAO, **extracao.detalhes()}
        if campos is not None:
            detalhes["campos_preenchidos"] = sorted(campos)
        self.repo.registrar_evento(item_id, "edicao", FONTE_AUTOMATICA, True, detalhes=detalhes)

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
        item = self.repo.item_da_thread(mensagem.thread_id)
        if item is not None:
            return self.reextrair(mensagem, item)

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

        # Extração fraca nunca retém (ADR-004): sem modelo, o item publica só com a classificação.
        extracao, motivo = self._extrair(mensagem, corpo, classificacao.tipo)
        item_id = self.repo.criar_item(
            thread_id=mensagem.thread_id,
            tipo=classificacao.tipo,
            descricao=(extracao.descricao if extracao else None) or descricao_inicial(mensagem, corpo),
            autor_email=mensagem.email_remetente,
            data_anuncio=mensagem.data_envio,
            revisar=classificacao.revisar,
            local=extracao.locais if extracao else [],
            localizacao=extracao.localizacao if extracao else None,
            setor=extracao.setor if extracao else None,
        )
        self.repo.registrar_evento(
            item_id, "classificacao", FONTE_AUTOMATICA, True,
            situacao_nova="aberto", detalhes=classificacao.detalhes(),
        )
        self._registrar_extracao(item_id, extracao, motivo)
        if classificacao.ja_encerrado:
            # Caso 8: "esqueci, já fui buscar, estou registrando". Nasce encerrado pelo próprio autor.
            self.repo.mudar_situacao(item_id, "encerrado", fonte_encerramento=FONTE_AUTOR)
            self.repo.registrar_evento(
                item_id, "desfecho", FONTE_AUTOR, True,
                situacao_anterior="aberto", situacao_nova="encerrado",
                detalhes={"regra": "anuncio_de_algo_ja_resolvido"},
            )
        return "item"

    def reextrair(self, mensagem: MensagemBruta, item) -> str:
        """O anúncio voltou sem `processamento` e a thread já tem item: a API publicou uma retida
        classificada pelo autor, ou a extração anterior falhou e alguém pediu reprocessamento.

        Não classifica de novo. Roda só a extração e preenche apenas o que está vazio: `local`,
        `localizacao`, `setor`, e `descricao` se ela for só o assunto. Nunca muda `tipo` nem `situacao`."""
        corpo = limpar_corpo(mensagem.corpo)
        extracao, motivo = self._extrair(mensagem, corpo, item.tipo)
        if extracao is None:
            self._registrar_extracao(item.id, None, motivo)
            return "item"
        campos = {}
        if not item.local and extracao.locais:
            campos["local"] = extracao.locais
        if item.localizacao is None and extracao.localizacao:
            campos["localizacao"] = extracao.localizacao
            campos["setor"] = extracao.setor
        elif not item.setor and extracao.setor and item.localizacao == "com um setor":
            campos["setor"] = extracao.setor
        descricao_era_o_assunto = not item.descricao or item.descricao == descricao_inicial(mensagem, corpo)
        if descricao_era_o_assunto and extracao.descricao and extracao.descricao != item.descricao:
            campos["descricao"] = extracao.descricao
        self.repo.atualizar_campos(item.id, campos)
        self._registrar_extracao(item.id, extracao, None, campos=campos)
        return "item"

    def processar_resposta(self, mensagem: MensagemBruta, anuncio: Optional[MensagemBruta]) -> Optional[str]:
        """US-10: a resposta pode reivindicar, encerrar ou corrigir o local do item da thread.

        Sem item na thread (anúncio retido, ainda pendente ou thread sem anúncio da lista), a
        resposta fica pendente: quando a API publicar a retida, o próximo ciclo a processa na ordem.
        Cada resposta gera no máximo um evento; a que não diz nada só é marcada `evento`.
        """
        if anuncio is None:
            return None
        item = self.repo.item_da_thread(mensagem.thread_id)
        if item is None:
            return None

        thread = self.repo.mensagens_da_thread(mensagem.thread_id)
        respostas = [
            RespostaAnterior(m.email_remetente, m.data_envio)
            for m in thread
            if m.veio_da_lista and m.mensagem_id != anuncio.mensagem_id
            and (m.data_envio is None or mensagem.data_envio is None or m.data_envio <= mensagem.data_envio)
        ]
        decisao = decidir(
            item_tipo=item.tipo,
            item_situacao=item.situacao,
            item_local=list(item.local or []),
            item_localizacao=item.localizacao,
            autor_email=item.autor_email,
            remetente_email=mensagem.email_remetente,
            texto_novo=limpar_corpo(mensagem.corpo, so_texto_novo=True),
            respostas_ate_aqui=respostas,
        )
        if decisao is None:
            return "evento"

        if decisao.aplicado and decisao.situacao_nova and decisao.situacao_nova != item.situacao:
            self.repo.mudar_situacao(
                item.id, decisao.situacao_nova,
                fonte_encerramento=decisao.fonte_encerramento, revisar=decisao.revisar,
            )
        if decisao.aplicado and decisao.campos:
            self.repo.atualizar_campos(item.id, decisao.campos)
        self.repo.registrar_evento(
            item.id, decisao.tipo_evento, decisao.fonte, decisao.aplicado,
            situacao_anterior=decisao.situacao_anterior,
            situacao_nova=decisao.situacao_nova,
            motivo_recusa=decisao.motivo_recusa,
            detalhes={**decisao.detalhes, "mensagem_bruta_id": mensagem.id},
        )
        return "evento"

    # ------------------------------------------------------------------ ciclo
    def executar_ciclo(self, fonte: FonteMensagens) -> ResumoCiclo:
        resumo = ResumoCiclo()
        self.ingerir(fonte, resumo)
        self.processar_pendentes(resumo)
        return resumo
