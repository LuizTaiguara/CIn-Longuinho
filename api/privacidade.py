"""Privacidade: mascaramento determinístico e logs sem e-mail (US-05, invariante 1).

O mascaramento é feito no servidor, por regra fixa, antes de a API responder. Formato que a
regra não reconhece escapa; cada formato novo encontrado vira caso de teste
(`api/testes/test_privacidade.py`).
"""

from __future__ import annotations

import logging
import re

MASCARA_EMAIL = "[e-mail mascarado]"

# Qualquer palavra com @ no meio: mais largo que um e-mail válido de propósito. Na dúvida,
# mascara (`fulano@cin`, `<fulano@cin.ufpe.br>`, `mailto:fulano@x.com`). Cobre também o `@`
# codificado em URL (`%40`), que aparece na query registrada no log de acesso.
_EMAIL = re.compile(
    r"[^\s<>()\[\]{}\"',;:@&=?/]+(?:@|%40)[^\s<>()\[\]{}\"',;:@&=?/]+", re.IGNORECASE
)


def mascarar_emails(texto: str) -> str:
    return _EMAIL.sub(MASCARA_EMAIL, texto)


MASCARA_TELEFONE = "[telefone mascarado]"

# Telefones brasileiros nos formatos comuns:
#   (81) 9 9999-9999 · (81) 99999-9999 · 81 99999-9999 · 81999999999 · +55 81 99999-9999
#   +55 (81) 9 9999-9999 · 5581999999999 · 081 99999-9999 · 99999-9999 · 9 9999-9999 · 9999-9999
# Oito dígitos seguidos (com ou sem separador no meio) bastam para mascarar: na dúvida, esconde.
_TELEFONE = re.compile(
    r"""
    (?<![\w@])
    (?:\+?\s?55[\s.-]*)?                     # país
    (?:\(\s?0?\d{2}\s?\)[\s.-]*               # DDD entre parênteses
       |0?\d{2}[\s.-]+                       # DDD seguido de separador
       |0?\d{2}(?=9?\d{8}(?!\d)))?            # DDD colado no número
    (?:9[\s.-]?)?\d{4}[\s.-]?\d{4}            # número
    (?![\w@])
    """,
    re.VERBOSE,
)


def mascarar_telefones(texto: str) -> str:
    return _TELEFONE.sub(MASCARA_TELEFONE, texto)


def mascarar(texto: str | None) -> str | None:
    """Mascara tudo o que a regra reconhece como contato pessoal: e-mail e telefone."""
    if texto is None:
        return None
    return mascarar_telefones(mascarar_emails(texto))


# ---------------------------------------------------------------------------
# Logs sem e-mail
# ---------------------------------------------------------------------------


def _mascarar_argumento(valor):
    if isinstance(valor, (int, float, bool)) or valor is None:
        return valor
    return mascarar_emails(str(valor))


def _mascarar_registro(registro: logging.LogRecord) -> None:
    if isinstance(registro.msg, str):
        registro.msg = mascarar_emails(registro.msg)
    elif registro.msg is not None:
        registro.msg = mascarar_emails(str(registro.msg))
    if isinstance(registro.args, tuple):
        registro.args = tuple(_mascarar_argumento(a) for a in registro.args)
    elif isinstance(registro.args, dict):
        registro.args = {k: _mascarar_argumento(v) for k, v in registro.args.items()}
    if registro.exc_info:
        # O rastro pode trazer valores do banco: vira texto mascarado e some como objeto.
        registro.exc_text = mascarar_emails(logging.Formatter().formatException(registro.exc_info))
        registro.exc_info = None
    if registro.stack_info:
        registro.stack_info = mascarar_emails(registro.stack_info)


_fabrica_original = None


def instalar_mascara_de_logs() -> None:
    """Todo registro de log do processo nasce mascarado, de qualquer logger (uvicorn incluso).

    Usa a fábrica de LogRecord, e não um `Filter`, porque filtro de logger não vale para
    registros que chegam por propagação, e o handler pode ser trocado pelo servidor.
    """
    global _fabrica_original
    if _fabrica_original is not None:
        return
    _fabrica_original = logging.getLogRecordFactory()

    def fabrica(*args, **kwargs):
        registro = _fabrica_original(*args, **kwargs)
        _mascarar_registro(registro)
        return registro

    logging.setLogRecordFactory(fabrica)
