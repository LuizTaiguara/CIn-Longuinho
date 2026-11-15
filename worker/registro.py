"""Configuração de log do worker. Nenhum endereço de e-mail chega ao log (invariante 1).

O filtro mascara qualquer coisa com cara de e-mail na mensagem final, inclusive em argumentos e
em texto de exceção. É uma rede de segurança: o código já evita logar remetente e corpo.
"""
import logging
import re
import sys

PADRAO_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
MASCARA = "[e-mail mascarado]"


def mascarar_emails(texto: str) -> str:
    return PADRAO_EMAIL.sub(MASCARA, texto)


class FiltroSemEmail(logging.Filter):
    def filter(self, registro: logging.LogRecord) -> bool:
        mensagem = registro.getMessage()
        registro.msg = mascarar_emails(mensagem)
        registro.args = None
        if registro.exc_info:
            # O rastro pode conter dado da mensagem; o log guarda só o tipo e o texto mascarado.
            tipo, valor, _ = registro.exc_info
            registro.msg += f" ({tipo.__name__}: {mascarar_emails(str(valor))})"
            registro.exc_info = None
            registro.exc_text = None
        return True


def configurar_log(nivel: int = logging.INFO) -> None:
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    for h in list(raiz.handlers):
        raiz.removeHandler(h)
    manipulador = logging.StreamHandler(sys.stderr)
    manipulador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    manipulador.addFilter(FiltroSemEmail())
    raiz.addHandler(manipulador)
