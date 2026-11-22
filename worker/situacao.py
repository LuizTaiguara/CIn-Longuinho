"""Situação do item a partir das respostas na thread (US-10). Regras determinísticas, sem LLM.

Para cada resposta (mensagem da lista que não é o anúncio) numa thread que já tem item, o
pipeline gera **no máximo um** evento e aplica a transição só se ela for válida:

| Quem responde | O que diz | Efeito |
|---|---|---|
| Não é o autor | "é meu", "acho que é minha", "acredito que pode ser minha" | `aberto → reivindicado` (detecção automática) |
| Não é o autor, num **perdido** | "está aqui", "está comigo", "achei ele", "disponível para retirada" | `aberto → reivindicado` |
| O autor | "encontrei", "encontraram", "já peguei", "achei já", "resolvido", "devolvido" | `→ encerrado`, "confirmação do autor" |
| Não é o autor | "foi resolvido, ela achou", "item devolvido" | `→ encerrado`, "terceiro", `revisar = TRUE` |
| Qualquer um | só "achei!" | evento com `aplicado = FALSE`; nada muda |
| O autor, num item reivindicado | "não tem garrafa verde" (desmentido) | evento com `aplicado = FALSE`; nunca retrocede |
| O autor de um achado | "está comigo", "deixei na SecGrad" | muda `localizacao` (mesmos padrões fechados do anúncio) |
| O autor | só um local ("Grad 3") | corrige `local` |
| Não é o autor | só um local | evento com `aplicado = FALSE`; `local` não muda (casos 4 e 21) |

Autor é quem tem o **mesmo endereço** do anúncio (compara o e-mail, não o nome).

**Defesa contra piada** (caso 6, decisão do PO em 14/10/2026): uma reivindicação não vale se a
própria mensagem tem marca de piada (kkk, haha, pix...) ou se a thread virou zoeira, isto é,
se em algum momento três ou mais pessoas diferentes, fora o autor, responderam em dez minutos.
Recusar uma reivindicação deixa o item `aberto`, que promete menos do que `reivindicado`.
A defesa não vale para desfecho de terceiro: o PO decidiu que ele encerra mesmo em piada, com o
catálogo mostrando "encerrado segundo terceiro".
"""
import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional, Tuple

from worker.extrator import localizacao_declarada, locais_por_regra
from worker.texto import normalizar

FONTE_AUTOMATICA = "detecção automática"
FONTE_AUTOR = "confirmação do autor"
FONTE_TERCEIRO = "terceiro"

JANELA_ZOEIRA = timedelta(minutes=10)
PESSOAS_ZOEIRA = 3

_NEGACAO = re.compile(r"\bnao\s+(?:\w+\s+)?(?:encontr|ach|peg|recuper|resolv|devolv)\w*")

REIVINDICACAO = re.compile(
    r"\b(?:e|eh|sao)\s+(?:o |a |os |as )?(?:meu|minha|meus|minhas)\b"
    r"|\b(?:acho|acredito|creio)\s+que\s+(?:e|eh|seja|sejam|pode ser|possa ser|posso ser)\s+(?:o |a )?(?:meu|minha|meus|minhas)\b"
    r"|\b(?:pode|possa|posso)\s+ser\s+(?:o |a )?(?:meu|minha|meus|minhas)\b"
)
# Num perdido, quem não é o autor dizendo que o objeto está com ele também reivindica.
ESTA_COMIGO = re.compile(
    r"\b(?:esta|ta|estao|tao|estava|ficou)\s+(?:aqui|comigo|com a gente|conosco|na secgrad|na secretaria)\b"
    r"|\b(?:achei|encontrei|achamos|encontramos)\s+(?:ele|ela|eles|elas|o seu|a sua|os seus|as suas|seu|sua)\b"
    r"|\bdisponive(?:l|is) para retirada\b|\bpode vir (?:retirar|buscar|pegar)\b"
    r"|\bdeixei\s+(?:na|no)\s+(?:secgrad|secretaria|gerinfra|portaria|recepcao)\b"
)
DESFECHO_AUTOR = re.compile(
    r"\bencontraram\b|\bacharam\b|\bencontrei\b|\brecuperei\b"
    r"|\bja\s+(?:peguei|recuperei|encontrei|achei|busquei|retirei|devolvi|entreguei)\b"
    r"|\bachei\s+ja\b|\bresolvid[oa]\b|\bdevolvid[oa]\b|\bentreguei\b"
    r"|\b(?:o dono|a dona)\s+(?:ja\s+)?(?:pegou|buscou|retirou|apareceu)\b"
)
DESFECHO_TERCEIRO = re.compile(
    r"\bresolvid[oa]\b|\bdevolvid[oa]\b|\bfoi entregue\b|\bja foi (?:entregue|retirad[oa])\b"
    r"|\b(?:ela|ele)\s+(?:ja\s+)?(?:achou|encontrou|pegou|recuperou|buscou)\b"
    r"|\b(?:achou|encontrou|pegou|recuperou)\s+(?:o seu|a sua|seu|sua)\b"
)
AMBIGUO = re.compile(r"^(?:achei|encontrei)\s*[!.]*$")
DESMENTIDO = re.compile(r"\bnao\s+(?:tem|ha|e|eh|era|sao)\b")
MARCAS_DE_PIADA = re.compile(r"k{3,}|\b(?:ha){2,}\b|\b(?:rs){2,}\b|\bpix\b|😂|🤣|[:=;]p\b", re.IGNORECASE)
SAUDACOES = re.compile(r"\b(?:oi|ola|oie|bom dia|boa tarde|boa noite|pessoal|gente|e|eh|na verdade|foi|no|na|sala)\b")


@dataclass
class RespostaAnterior:
    """O que a defesa contra piada precisa saber das respostas anteriores da thread."""

    email: str
    data_envio: object


@dataclass
class Decisao:
    tipo_evento: str
    fonte: str
    aplicado: bool
    situacao_anterior: Optional[str] = None
    situacao_nova: Optional[str] = None
    motivo_recusa: Optional[str] = None
    fonte_encerramento: Optional[str] = None
    revisar: Optional[bool] = None
    campos: dict = field(default_factory=dict)  # local, localizacao, setor
    detalhes: dict = field(default_factory=dict)


def thread_virou_zoeira(respostas: List[RespostaAnterior], autor_email: str) -> bool:
    """Três ou mais pessoas diferentes, fora o autor, respondendo dentro de dez minutos."""
    outras = sorted(
        (r for r in respostas if r.email != autor_email and r.data_envio is not None),
        key=lambda r: r.data_envio,
    )
    for i, inicio in enumerate(outras):
        pessoas = {r.email for r in outras[i:] if r.data_envio - inicio.data_envio <= JANELA_ZOEIRA}
        if len(pessoas) >= PESSOAS_ZOEIRA:
            return True
    return False


def _so_um_local(texto_normalizado: str) -> Optional[List[str]]:
    """A resposta é só um local ("Grad 3", "na verdade foi na E132")? Devolve os locais."""
    locais = locais_por_regra(texto_normalizado)
    if not locais:
        return None
    resto = texto_normalizado
    resto = re.sub(r"\bgrad\s*0?\d\b|\b[a-e]\s?-?\d{3}\b|\blab\w*\s+de\s+\w+", " ", resto)
    resto = SAUDACOES.sub(" ", resto)
    resto = re.sub(r"[^\w]+", " ", resto).strip()
    return locais if len(resto.split()) <= 1 else None


def _transicao(situacao: str, nova: str) -> Tuple[bool, Optional[str]]:
    """Confere a transição antes do UPDATE (o trigger do banco é só rede de segurança)."""
    if situacao == "encerrado":
        return False, "item já encerrado: a situação não muda (invariante 2)"
    if situacao == nova:
        return False, f"item já está {nova}"
    if situacao == "aberto" and nova in ("reivindicado", "encerrado"):
        return True, None
    if situacao == "reivindicado" and nova == "encerrado":
        return True, None
    return False, f"transição {situacao} → {nova} não permitida (invariante 2)"


def decidir(
    item_tipo: str,
    item_situacao: str,
    item_local: List[str],
    item_localizacao: Optional[str],
    autor_email: str,
    remetente_email: str,
    texto_novo: str,
    respostas_ate_aqui: List[RespostaAnterior],
) -> Optional[Decisao]:
    """Decide o evento de uma resposta. `texto_novo` é só o que a pessoa escreveu (sem citação).
    `respostas_ate_aqui` inclui a própria resposta. Devolve None se a resposta não diz nada."""
    eh_autor = bool(autor_email) and remetente_email == autor_email
    bruto = normalizar(texto_novo)
    texto = _NEGACAO.sub(" ", bruto)
    if not texto:
        return None

    def mudar(tipo_evento, fonte, nova, regra, **extra):
        ok, motivo = _transicao(item_situacao, nova)
        return Decisao(
            tipo_evento, fonte, ok, situacao_anterior=item_situacao, situacao_nova=nova,
            motivo_recusa=motivo, detalhes={"regra": regra, "autor": eh_autor},
            **(extra if ok else {}),
        )

    def recusar(tipo_evento, fonte, regra, motivo, nova=None, **detalhes):
        return Decisao(
            tipo_evento, fonte, False, situacao_anterior=item_situacao, situacao_nova=nova,
            motivo_recusa=motivo, detalhes={"regra": regra, "autor": eh_autor, **detalhes},
        )

    if AMBIGUO.match(re.sub(r"[^\w!. ]", "", bruto).strip()):
        fonte = FONTE_AUTOR if eh_autor else FONTE_TERCEIRO
        return recusar("desfecho", fonte, "resposta_ambigua", "resposta ambígua: a situação não muda")

    if eh_autor:
        if DESFECHO_AUTOR.search(texto):
            return mudar("desfecho", FONTE_AUTOR, "encerrado", "desfecho_pelo_autor", fonte_encerramento=FONTE_AUTOR)
        if item_situacao == "reivindicado" and DESMENTIDO.search(bruto):
            return recusar(
                "reivindicacao", FONTE_AUTOR, "desmentido_do_autor",
                "o autor contestou a reivindicação; a situação não retrocede (invariante 2)", nova="aberto",
            )
        if item_tipo == "achado":
            localizacao, setor = localizacao_declarada(texto_novo)
            if localizacao and (localizacao != item_localizacao or setor):
                return Decisao(
                    "edicao", FONTE_AUTOR, True,
                    campos={"localizacao": localizacao, "setor": setor},
                    detalhes={"regra": "localizacao_declarada_pelo_autor", "localizacao": localizacao, "setor": setor},
                )
        locais = _so_um_local(texto)
        if locais and locais != item_local:
            return Decisao(
                "edicao", FONTE_AUTOR, True, campos={"local": locais},
                detalhes={"regra": "correcao_de_local_pelo_autor", "local_anterior": item_local, "local": locais},
            )
        return None

    # Quem responde não é o autor.
    if DESFECHO_TERCEIRO.search(texto):
        return mudar("desfecho", FONTE_TERCEIRO, "encerrado", "desfecho_por_terceiro",
                     fonte_encerramento=FONTE_TERCEIRO, revisar=True)

    reivindica = REIVINDICACAO.search(texto) or (item_tipo == "perdido" and ESTA_COMIGO.search(texto))
    if reivindica:
        if MARCAS_DE_PIADA.search(texto_novo):
            return recusar("reivindicacao", FONTE_AUTOMATICA, "reivindicacao_em_tom_de_piada",
                           "reivindicação com marca de piada não muda a situação", nova="reivindicado")
        if thread_virou_zoeira(respostas_ate_aqui, autor_email):
            return recusar("reivindicacao", FONTE_AUTOMATICA, "thread_em_zoeira",
                           "várias pessoas respondendo em poucos minutos: tratada como piada", nova="reivindicado")
        return mudar("reivindicacao", FONTE_AUTOMATICA, "reivindicado", "reivindicacao")

    locais = _so_um_local(texto)
    if locais:
        return recusar("edicao", FONTE_TERCEIRO, "correcao_de_local_por_terceiro",
                       "só o autor corrige o local; a sugestão fica registrada", local_sugerido=locais)
    return None
