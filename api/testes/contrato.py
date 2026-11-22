"""Conferência das respostas contra shared/openapi.yaml.

Para cada resposta: todos os `required` do schema presentes, nenhuma chave fora de
`properties`, tipos e enums respeitados. Resolve `$ref`, `oneOf` e `type` com `null`.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

ARQUIVO = Path(__file__).resolve().parents[2] / "shared" / "openapi.yaml"


@lru_cache(maxsize=1)
def contrato() -> dict:
    return yaml.safe_load(ARQUIVO.read_text(encoding="utf-8"))


def _resolver(schema: dict) -> dict:
    while "$ref" in schema:
        caminho = schema["$ref"].removeprefix("#/").split("/")
        alvo = contrato()
        for parte in caminho:
            alvo = alvo[parte]
        schema = alvo
    return schema


def _tipos(schema: dict) -> list[str]:
    tipo = schema.get("type")
    if tipo is None:
        return []
    return tipo if isinstance(tipo, list) else [tipo]


def conferir(schema: dict, valor, caminho: str = "$") -> list[str]:
    """Devolve a lista de problemas (vazia quando o valor segue o schema)."""
    schema = _resolver(schema)
    if "oneOf" in schema:
        tentativas = [conferir(opcao, valor, caminho) for opcao in schema["oneOf"]]
        if any(not t for t in tentativas):
            return []
        return [f"{caminho}: não casa com nenhuma opção de oneOf ({tentativas})"]

    tipos = _tipos(schema)
    if valor is None:
        if "null" in tipos or (not tipos and None in schema.get("enum", [])):
            return []
        return [f"{caminho}: null não permitido"]
    if "enum" in schema and valor not in schema["enum"]:
        return [f"{caminho}: {valor!r} fora do enum {schema['enum']}"]

    problemas: list[str] = []
    if "object" in tipos:
        if not isinstance(valor, dict):
            return [f"{caminho}: esperava objeto"]
        propriedades = schema.get("properties", {})
        for obrigatorio in schema.get("required", []):
            if obrigatorio not in valor:
                problemas.append(f"{caminho}: falta o campo obrigatório {obrigatorio!r}")
        for chave, sub in valor.items():
            if chave not in propriedades:
                problemas.append(f"{caminho}: chave {chave!r} fora do contrato")
            else:
                problemas += conferir(propriedades[chave], sub, f"{caminho}.{chave}")
    elif "array" in tipos:
        if not isinstance(valor, list):
            return [f"{caminho}: esperava lista"]
        for i, sub in enumerate(valor):
            problemas += conferir(schema.get("items", {}), sub, f"{caminho}[{i}]")
    elif "string" in tipos:
        if not isinstance(valor, str):
            return [f"{caminho}: esperava texto"]
        if schema.get("format") == "date-time" and not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", valor):
            problemas.append(f"{caminho}: {valor!r} não é date-time")
        if "minLength" in schema and len(valor) < schema["minLength"]:
            problemas.append(f"{caminho}: menor que minLength")
    elif "integer" in tipos:
        if not isinstance(valor, int) or isinstance(valor, bool):
            return [f"{caminho}: esperava inteiro"]
    elif "boolean" in tipos:
        if not isinstance(valor, bool):
            return [f"{caminho}: esperava booleano"]
    return problemas


def schema_da_resposta(metodo: str, caminho: str, status: int) -> dict | None:
    operacao = contrato()["paths"][caminho][metodo.lower()]
    resposta = operacao["responses"].get(str(status))
    if resposta is None:
        raise AssertionError(f"{metodo} {caminho} não prevê status {status} no contrato")
    conteudo = resposta.get("content", {}).get("application/json")
    return conteudo["schema"] if conteudo else None


def conferir_resposta(resposta, metodo: str, caminho: str) -> None:
    """Falha o teste se a resposta HTTP não segue o contrato para aquele status."""
    schema = schema_da_resposta(metodo, caminho, resposta.status_code)
    if schema is None:
        return
    problemas = conferir(schema, resposta.json())
    assert not problemas, f"{metodo} {caminho} {resposta.status_code}: " + "; ".join(problemas)
