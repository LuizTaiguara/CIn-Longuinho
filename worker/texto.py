"""Limpeza do texto das mensagens antes de classificar e extrair.

Tudo aqui é determinístico (ADR-009). O texto dos e-mails é dado, nunca instrução.

- `limpar_corpo` tira citações (formato do Gmail em português, inglês e francês), linhas `> ...`,
  marcadores `[image: ...]` e a assinatura (`--`). Num encaminhamento (português, espanhol, inglês),
  tira o bloco de cabeçalho (De/Data/Assunto/Para...) e, por padrão, **mantém** o texto encaminhado:
  no anúncio, ele é o conteúdo (casos 20 e 28). Numa resposta, o pipeline pede `so_texto_novo=True`.
- `limpar_assunto` tira `Re:`/`Fwd:` e as etiquetas entre colchetes (`[PERDIDO]`, `[staff]`...).
- `normalizar` deixa minúsculo e sem acento, para as regras compararem sem depender de grafia.
"""
import re
import unicodedata
from typing import List

# "Em qui., 1 de out. de 2026 às 18:36, Fulano\n<fic...> escreveu:" (pode quebrar em até 3 linhas)
_ATRIBUICAO_CITACAO = re.compile(
    r"^[ \t]*(?:Em|On|Le)\b[^\n]*(?:\n[^\n]*){0,2}?(?:escreveu|wrote|a\s+écrit)\s*:[ \t]*$",
    re.MULTILINE | re.IGNORECASE,
)
_MARCADOR_ENCAMINHAMENTO = re.compile(
    r"^[ \t]*-{2,}\s*(?:Mensagem encaminhada|Mensaje reenviado|Forwarded message|Mensagem original)\s*-{2,}[ \t]*$",
    re.MULTILINE | re.IGNORECASE,
)
_IMAGEM = re.compile(r"^\s*\[image:[^\]]*\]\s*$", re.MULTILINE | re.IGNORECASE)
_ASSINATURA = re.compile(r"^--\s*$", re.MULTILINE)
_PREFIXO_RESPOSTA = re.compile(r"^\s*(?:(?:re|res|fw|fwd|enc|tr)\s*:\s*)+", re.IGNORECASE)
_ETIQUETA = re.compile(r"\[[^\]]*\]")
_ESPACOS = re.compile(r"[ \t]+")


def normalizar(texto: str) -> str:
    """Minúsculo, sem acento, com espaços simples. `Grad 5` e `grad  5` ficam iguais."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def _tirar_cabecalho_encaminhado(trecho: str) -> str:
    """Remove o bloco De:/Fecha:/Asunto:/Para: que segue o marcador, até a primeira linha vazia."""
    linhas = trecho.split("\n")
    i = 0
    while i < len(linhas) and linhas[i].strip():
        i += 1
    return "\n".join(linhas[i:])


def limpar_corpo(corpo: str, so_texto_novo: bool = False) -> str:
    texto = (corpo or "").replace("\r\n", "\n").replace("\r", "\n")

    # 1. Citação: tudo a partir da atribuição "Em ... escreveu:" é texto antigo.
    m = _ATRIBUICAO_CITACAO.search(texto)
    if m:
        texto = texto[: m.start()]
    texto = "\n".join(l for l in texto.split("\n") if not l.lstrip().startswith(">"))

    # 2. Encaminhamento.
    partes = _MARCADOR_ENCAMINHAMENTO.split(texto)
    if len(partes) > 1:
        if so_texto_novo:
            texto = partes[0]
        else:
            # Texto novo + cada trecho encaminhado sem o cabeçalho. Reforços repetem o mesmo
            # texto várias vezes (caso 28); a repetição não muda a classificação.
            texto = "\n".join([partes[0]] + [_tirar_cabecalho_encaminhado(p.lstrip("\n")) for p in partes[1:]])

    # 3. Imagens inline e assinatura.
    texto = _IMAGEM.sub("", texto)
    m = _ASSINATURA.search(texto)
    if m:
        texto = texto[: m.start()]

    linhas = [_ESPACOS.sub(" ", l).strip() for l in texto.split("\n")]
    return "\n".join(linhas).strip()


def etiquetas_do_assunto(assunto: str) -> List[str]:
    """Etiquetas entre colchetes, normalizadas: `[PERDIDO] x` → ['perdido']."""
    return [normalizar(e.strip("[]")) for e in _ETIQUETA.findall(assunto or "")]


def limpar_assunto(assunto: str) -> str:
    """`Re: [staff] [PERDIDO] Garrafa` → `Garrafa`."""
    texto = assunto or ""
    anterior = None
    while anterior != texto:
        anterior = texto
        texto = _PREFIXO_RESPOSTA.sub("", texto)
        texto = _ETIQUETA.sub(" ", texto)
    texto = re.sub(r"\s+", " ", texto).strip(" -–—:|")
    return texto.strip()
