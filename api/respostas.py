"""Montagem das respostas do contrato a partir das linhas do banco.

Cada função monta o objeto **campo a campo**, por lista branca. Não existe caminho de
"devolver a linha inteira": um campo novo no banco só chega ao cliente se for escrito aqui,
e nenhum campo de e-mail existe no contrato (invariante 1, SCRUM-101).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from api.privacidade import mascarar

PADRAO_ID_ITEM = re.compile(r"^item_([1-9][0-9]{0,17})$")
PADRAO_ID_RETIDA = re.compile(r"^retida_([1-9][0-9]{0,17})$")


def id_item(numero: int) -> str:
    return f"item_{numero}"


def numero_do_id(texto: str, padrao: re.Pattern = PADRAO_ID_ITEM) -> int | None:
    casamento = padrao.match(texto or "")
    return int(casamento.group(1)) if casamento else None


def data_iso(valor: datetime | None) -> str | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _setor(linha: dict) -> str | None:
    # Contrato: `setor` só vem preenchido quando `localizacao` é "com um setor".
    return mascarar(linha.get("setor")) if linha.get("localizacao") == "com um setor" else None


def _data_atualizacao(linha: dict) -> str | None:
    atualizado, criado = linha.get("atualizado_em"), linha.get("criado_em")
    if atualizado is None or atualizado == criado:
        return None
    return data_iso(atualizado)


def item_resumo(linha: dict) -> dict:
    return {
        "id": id_item(linha["id"]),
        "tipo": linha["tipo"],
        # Texto livre pode trazer contato copiado da mensagem: sai mascarado também.
        "descricao": mascarar(linha.get("descricao") or ""),
        "local": [mascarar(nome) for nome in (linha.get("local") or [])],
        "situacao": linha["situacao"],
        "localizacao": linha.get("localizacao"),
        "setor": _setor(linha),
        "foto_url": linha.get("foto_url"),
        "data_registro": data_iso(linha["data_anuncio"]),
        "data_atualizacao": _data_atualizacao(linha),
        "fonte_encerramento": linha.get("fonte_encerramento"),
        "data_situacao": data_iso(linha["data_situacao"]),
        "revisar": bool(linha.get("revisar")),
    }


def item_detalhe(linha: dict, texto_original: str | None) -> dict:
    return {
        **item_resumo(linha),
        "pode_gerir": bool(linha.get("pode_gerir")),
        "texto_original": texto_original,
    }


def local(linha: dict) -> dict:
    return {"nome": linha["nome"], "bloco": linha.get("bloco")}


def paginacao(pagina: int, limite: int, total: int) -> dict:
    total_paginas = max(1, -(-total // limite))
    return {
        "pagina_atual": pagina,
        "total_paginas": total_paginas,
        "total_itens": total,
        "limite": limite,
    }
