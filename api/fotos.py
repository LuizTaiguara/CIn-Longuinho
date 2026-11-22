"""Fotos dos anúncios (US-06): validação pelos bytes, gravação e nome aleatório.

- O tipo é conferido pelo conteúdo (Pillow), nunca pela extensão nem pelo Content-Type.
- Aceita JPEG, PNG e WebP até 5 MB.
- A imagem é regravada sem metadados: o EXIF de uma foto de celular pode trazer a localização
  de onde ela foi tirada (dado pessoal de quem anunciou). A orientação é aplicada antes.
- Nada é apagado: a foto anterior do item continua no disco quando outra a substitui.
"""

from __future__ import annotations

import io
import secrets
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

LIMITE_BYTES = 5 * 1024 * 1024
LIMITE_PIXELS = 40_000_000  # acima disso a imagem é recusada (bomba de descompressão)
FORMATOS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}
TIPO_POR_EXTENSAO = {ext: tipo for ext, tipo in FORMATOS.values()}
PADRAO_NOME = r"^[0-9a-f]{32}\.(jpg|png|webp)$"


class FotoInvalida(ValueError):
    pass


class FotoGrande(ValueError):
    pass


def preparar(conteudo: bytes) -> tuple[bytes, str]:
    """Confere a imagem e devolve (bytes regravados sem metadados, extensão)."""
    if len(conteudo) > LIMITE_BYTES:
        raise FotoGrande()
    if not conteudo:
        raise FotoInvalida()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(conteudo)) as conferida:
                formato = conferida.format
                if formato not in FORMATOS or conferida.width * conferida.height > LIMITE_PIXELS:
                    raise FotoInvalida()
                conferida.verify()
            with Image.open(io.BytesIO(conteudo)) as imagem:
                imagem.load()
                imagem = ImageOps.exif_transpose(imagem)
                if formato == "JPEG" and imagem.mode not in ("RGB", "L"):
                    imagem = imagem.convert("RGB")
                saida = io.BytesIO()
                opcoes = {"quality": 90} if formato in ("JPEG", "WEBP") else {}
                imagem.save(saida, format=formato, **opcoes)
    except FotoInvalida:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise FotoInvalida() from None
    return saida.getvalue(), FORMATOS[formato][0]


def gravar(pasta: str | Path, conteudo: bytes, extensao: str) -> str:
    """Grava com nome aleatório e devolve o nome do arquivo."""
    destino = Path(pasta)
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"{secrets.token_hex(16)}.{extensao}"
    (destino / nome).write_bytes(conteudo)
    return nome
