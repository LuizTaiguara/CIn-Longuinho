"""Classificador determinístico do anúncio (US-02, ADR-004, ADR-009). Sem LLM, sem modelo.

Portão de duas perguntas, nessa ordem:
1. **É achados e perdidos?** Se não → quarentena `fora_de_tema`.
2. **Achado ou perdido?** Se não dá para saber → quarentena `direcao_ambigua`.
Depois, confiança em três faixas: **alta** publica; **média** publica com `item.revisar = TRUE`;
**baixa** → quarentena `confianca_baixa`.

As regras trabalham sobre o texto limpo (sem citação, sem cabeçalho de encaminhamento, sem
assinatura) e normalizado (minúsculo, sem acento). Cada regra que dispara vira um "sinal" com peso:

| Onde | Peso | Exemplo |
|---|---|---|
| Verbo ou expressão no corpo | 3 | "encontrei", "perdi", "se alguém encontrar", "os donos" |
| Verbo no assunto | 2 | "Perdi uma garrafa cinza..." (caso 25, sem corpo) |
| Etiqueta do assunto (`[PERDIDO]`) | 0 | só indica que o tema é achados e perdidos; nunca decide a direção |

A etiqueta não decide porque mente com frequência: `[PERDIDO]` com "encontrei" no corpo é achado
(casos 1, 2, 3, 14) e `[PERDIDO]` com "Mouse deixado no Grad02" é ambíguo (caso 11).

Faixas: só um lado tem sinais → alta se houver sinal do corpo, média se só do assunto; os dois
lados têm sinais → média se a diferença for de pelo menos 3, baixa se menor; empate → ambígua.
Corpo vazio com foto e objeto no assunto → achado, média (caso 10, decisão do PO em 14/10/2026).
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from worker.texto import etiquetas_do_assunto, limpar_assunto, normalizar

CONFIANCA = {"alta": 0.9, "media": 0.6, "baixa": 0.3}

# A expressão "achados e perdidos" é o nome da lista, não um sinal de direção.
_NOME_DA_LISTA = re.compile(r"\bachados?\s*(?:e|/|&)\s*perdidos?\b|\bperdidos?\s*(?:e|/|&)\s*achados?\b")
# Negação tira o verbo do jogo: "fui lá e não encontrei" (caso 5), "não achei" (caso 19).
_NEGACAO = re.compile(r"\bnao\s+(?:\w+\s+)?(?:encontr|ach|perd|esquec)\w*")

PESO_CORPO = 3
PESO_ASSUNTO = 2

# (nome do sinal, padrão) sobre texto normalizado.
SINAIS_ACHADO_CORPO: List[Tuple[str, str]] = [
    ("verbo_achei", r"\b(?:encontrei|achei|achamos|encontramos|encontro)\b"),
    ("foi_achado", r"\b(?:encontrad|achad)[oa]s?\b"),
    ("se_encontra", r"\b(?:se encontra|se encontram|encontra-se|encontram-se)\b"),
    ("disponivel_retirada", r"\b(?:disponive(?:l|is) para retirada|para retirada|pode vir retirar)\b"),
    ("terceiros_perderam", r"\b(?:perderam|esqueceram|deixaram)\b"),
    ("tem_um_perdido", r"\b(?:tem|ha|havia|estava)\s+(?:um|uma|uns|umas|esse|essa|este|esta)\s+(?:[\w-]+\s+){0,3}?(?:perdid|esquecid|largad)\w*"),
    ("guardei", r"\bguardei\b"),
    ("vou_deixar", r"\b(?:vou|irei|ire|vamos)\s+deixar\b"),
    ("deixei_no_setor", r"\bdeixei\s+(?:na|no|com a|com o)\s+(?:portaria|secgrad|secretaria|gerinfra|recepcao|coordenacao)\b"),
    ("donos", r"\bdon[oa]s?\b"),
    ("como_seu", r"\b(?:como seu|como sua|se for (?:seu|sua|teu|tua)|reconhece-lo|reconhece-la)\b"),
    ("levei_por_engano", r"\b(?:levei|peguei)\b[\w ,]{0,40}\b(?:para casa|pra casa|por engano|achando que era)\b"),
    ("pertencente", r"\b(?:pertencente|pertence a)\b"),
]
SINAIS_PERDIDO_CORPO: List[Tuple[str, str]] = [
    ("verbo_perdi", r"\b(?:perdi|esqueci|perdemos|esquecemos)\b"),
    ("esquecendo_o_meu", r"\b(?:esquecendo|perdendo|deixei|esqueci)\s+(?:o |a |os |as )?(?:meu|minha|meus|minhas)\b"),
    ("alguem_viu", r"\balguem\s+(?:viu|achou|encontrou|ver|vir|achar|encontrar|encontre|ache)\b"),
    ("se_alguem_encontrar", r"\b(?:se|caso)\s+alguem\s+(?:o |a |os |as |ja )?(?:encontr|ach|ve|vir|vi)\w*"),
    ("quem_encontrou", r"\bquem\s+(?:o |a |os |as )?(?:encontrou|achou|encontrar|achar|tiver visto|tiver encontrado|tiver achado)\b"),
    ("recompensa_devolucao", r"\b(?:recompensa|agradeco (?:a )?devolucao)\b"),
]
SINAIS_ACHADO_ASSUNTO: List[Tuple[str, str]] = [
    ("assunto_achado", r"\b(?:encontrad|achad)[oa]s?\b|\b(?:encontrei|achei)\b|\bdisponivel para retirada\b"),
]
SINAIS_PERDIDO_ASSUNTO: List[Tuple[str, str]] = [
    ("assunto_perdi", r"\b(?:perdi|esqueci)\b|\balguem viu\b"),
]

# Anúncio de algo que a própria pessoa já recuperou (caso 8): vira item já encerrado.
JA_RESOLVIDO = re.compile(
    r"\bja\s+(?:fui buscar|busquei|peguei|recuperei|encontrei|achei|retirei|consegui (?:pegar|recuperar))\b"
    r"|\b(?:to|tou|estou)\s+registrando\b"
)

# Fora de tema que costuma usar a lista: pesquisa, pedido de descadastro, aviso de processo.
FORA_DE_TEMA: List[Tuple[str, str]] = [
    ("pesquisa", r"docs\.google\.com/forms|\bforms\b|\bformulario\b|\bquestionario\b|\bpesquisa\b"),
    ("descadastro", r"\breceber mais\b|\bsair da lista\b|\bdescadastr\w*|\bremover da lista\b|\bunsubscribe\b"),
    ("aviso_de_descarte", r"\bserao descartad\w*|\bprazo de retirada\b|\bdescarte\b"),
]

VOCABULARIO_TEMA = re.compile(r"\bperd\w*|\bachad\w*|\bencontr\w*|\besquec\w*|\bsumiu\b")
ETIQUETAS_TEMA = re.compile(r"perdid|achad|achados")

# Objetos comuns na lista (análise do corpus). Serve à regra do caso 10: corpo vazio, foto e
# objeto nomeado no assunto. A extração (US-03) não depende desta lista.
OBJETOS = [
    "garrafa", "garrafinha", "squeeze", "copo", "caneca", "fone", "fones", "airpods", "headset",
    "celular", "telefone", "aparelho", "iphone", "carregador", "cabo", "fonte", "mouse", "teclado",
    "notebook", "laptop", "tablet", "ipad", "caneta", "lapis", "estojo", "caderno", "livro", "agenda",
    "pendrive", "pen drive", "hd", "ssd", "calculadora", "oculos", "relogio", "pulseira", "anel",
    "colar", "brinco", "chave", "chaves", "chaveiro", "carteira", "documento", "rg", "cnh",
    "cracha", "cartao", "vem", "bolsa", "mochila", "sacola", "necessaire", "casaco", "jaqueta",
    "moletom", "blusa", "camisa", "camiseta", "bone", "chapeu", "guarda-chuva", "sombrinha",
    "batom", "nota", "dinheiro", "lousa", "lousinha", "marmita", "lancheira", "tupperware",
]
_OBJETO = re.compile(r"\b(?:" + "|".join(re.escape(o) for o in OBJETOS) + r")\b")


class ClassificadorIndisponivel(Exception):
    """Erro interno do classificador. A mensagem fica sem `processamento` e volta no próximo ciclo."""


@dataclass
class Classificacao:
    destino: str  # 'item' | 'quarentena'
    tipo: Optional[str] = None  # 'achado' | 'perdido'
    motivo_retencao: Optional[str] = None
    faixa: str = "baixa"  # 'alta' | 'media' | 'baixa'
    ja_encerrado: bool = False
    sinais: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def confianca(self) -> float:
        return CONFIANCA[self.faixa]

    @property
    def revisar(self) -> bool:
        return self.destino == "item" and self.faixa == "media"

    def detalhes(self) -> dict:
        return {
            "destino": self.destino,
            "tipo": self.tipo,
            "motivo_retencao": self.motivo_retencao,
            "faixa": self.faixa,
            "confianca": self.confianca,
            "ja_encerrado": self.ja_encerrado,
            "sinais": self.sinais,
        }


def _preparar(texto: str) -> str:
    t = normalizar(texto)
    t = _NOME_DA_LISTA.sub(" ", t)
    return _NEGACAO.sub(" ", t)


def _sinais(texto: str, regras: List[Tuple[str, str]]) -> List[str]:
    return [nome for nome, padrao in regras if re.search(padrao, texto)]


def nomeia_objeto(texto: str) -> bool:
    return bool(_OBJETO.search(normalizar(texto)))


def classificar(
    assunto: str,
    corpo_limpo: str,
    tem_imagem: bool = False,
    thread_incompleta: bool = False,
) -> Classificacao:
    """Classifica o anúncio. `corpo_limpo` já passou por `texto.limpar_corpo`."""
    assunto_limpo = limpar_assunto(assunto)
    etiquetas = etiquetas_do_assunto(assunto)
    corpo = _preparar(corpo_limpo)
    titulo = _preparar(assunto_limpo)

    sinais = {
        "achado": _sinais(corpo, SINAIS_ACHADO_CORPO) + _sinais(titulo, SINAIS_ACHADO_ASSUNTO),
        "perdido": _sinais(corpo, SINAIS_PERDIDO_CORPO) + _sinais(titulo, SINAIS_PERDIDO_ASSUNTO),
    }
    forca = {
        lado: sum(PESO_ASSUNTO if s.startswith("assunto_") else PESO_CORPO for s in lista)
        for lado, lista in sinais.items()
    }
    so_do_assunto = {lado: all(s.startswith("assunto_") for s in lista) for lado, lista in sinais.items()}

    # Thread cujo começo não chegou (caso 27): não há como saber o que foi anunciado.
    if thread_incompleta:
        sinais["regra"] = ["thread_incompleta"]
        return Classificacao("quarentena", motivo_retencao="confianca_baixa", faixa="baixa", sinais=sinais)

    # Pergunta 1: é achados e perdidos?
    fora = _sinais(normalizar(assunto_limpo + "\n" + corpo_limpo), FORA_DE_TEMA)
    if fora and max(forca.values()) < PESO_CORPO:
        sinais["fora_de_tema"] = fora
        return Classificacao("quarentena", motivo_retencao="fora_de_tema", sinais=sinais)

    corpo_vazio = not corpo.strip()
    if corpo_vazio and forca["achado"] == forca["perdido"] == 0:
        # Regra do caso 10: sem texto, com foto e com o objeto no assunto, é achado.
        if tem_imagem and nomeia_objeto(assunto_limpo):
            sinais["regra"] = ["sem_corpo_foto_objeto_no_assunto"]
            return Classificacao("item", tipo="achado", faixa="media", sinais=sinais)
        if not nomeia_objeto(assunto_limpo):
            return Classificacao("quarentena", motivo_retencao="sem_texto_e_sem_objeto", sinais=sinais)
        return Classificacao("quarentena", motivo_retencao="direcao_ambigua", sinais=sinais)

    tem_tema = (
        forca["achado"] + forca["perdido"] > 0
        or any(ETIQUETAS_TEMA.search(e) for e in etiquetas)
        or VOCABULARIO_TEMA.search(normalizar(assunto) + " " + normalizar(corpo_limpo))
    )
    if not tem_tema:
        return Classificacao("quarentena", motivo_retencao="fora_de_tema", sinais=sinais)

    # Pergunta 2: achado ou perdido?
    a, p = forca["achado"], forca["perdido"]
    if a == p:
        return Classificacao("quarentena", motivo_retencao="direcao_ambigua", sinais=sinais)
    tipo = "achado" if a > p else "perdido"
    vencedor, perdedor = max(a, p), min(a, p)

    if perdedor == 0:
        faixa = "media" if so_do_assunto[tipo] else "alta"
    elif vencedor - perdedor >= PESO_CORPO:
        faixa = "media"
    else:
        faixa = "baixa"

    if faixa == "baixa":
        return Classificacao("quarentena", tipo=None, motivo_retencao="confianca_baixa", faixa="baixa", sinais=sinais)

    ja_encerrado = tipo == "perdido" and bool(JA_RESOLVIDO.search(corpo))
    return Classificacao("item", tipo=tipo, faixa=faixa, ja_encerrado=ja_encerrado, sinais=sinais)
