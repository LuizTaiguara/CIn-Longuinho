"""Erros da API no formato `Erro` do contrato: `{codigo, mensagem}`.

Nenhuma resposta de erro ecoa o que o cliente mandou nem traz rastro de exceção: o valor
enviado pode conter um endereço de e-mail, e o rastro pode conter dado do banco.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.banco import BancoIndisponivel

log = logging.getLogger("api.erros")


class ErroApi(Exception):
    def __init__(self, status: int, codigo: str, mensagem: str) -> None:
        super().__init__(codigo)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem


def nao_encontrado() -> ErroApi:
    # Sempre a mesma resposta para inexistente, oculto ou retido: não revela existência.
    return ErroApi(404, "NAO_ENCONTRADO", "Item não encontrado.")


def parametros_invalidos(mensagem: str = "Parâmetros fora do contrato.") -> ErroApi:
    return ErroApi(400, "PARAMETROS_INVALIDOS", mensagem)


def nao_autenticado() -> ErroApi:
    return ErroApi(401, "NAO_AUTENTICADO", "Entre com a sua conta do CIn para continuar.")


def nao_autorizado() -> ErroApi:
    return ErroApi(403, "NAO_AUTORIZADO", "Só quem anunciou pode fazer isso neste item.")


def resposta_erro(status: int, codigo: str, mensagem: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"codigo": codigo, "mensagem": mensagem}, status_code=status, headers=headers)


_CODIGO_POR_STATUS = {
    400: "PARAMETROS_INVALIDOS",
    401: "NAO_AUTENTICADO",
    403: "NAO_AUTORIZADO",
    404: "NAO_ENCONTRADO",
    405: "METODO_NAO_PERMITIDO",
}


def instalar(app: FastAPI) -> None:
    @app.exception_handler(ErroApi)
    async def _erro_api(_: Request, erro: ErroApi) -> JSONResponse:
        return resposta_erro(erro.status, erro.codigo, erro.mensagem)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        # Só os nomes dos campos, nunca os valores recebidos.
        campos = sorted({str(e.get("loc", ["?"])[-1]) for e in erro.errors()})
        return resposta_erro(
            400, "PARAMETROS_INVALIDOS", "Parâmetros fora do contrato: " + ", ".join(campos) + "."
        )

    @app.exception_handler(BancoIndisponivel)
    async def _banco(_: Request, erro: BancoIndisponivel) -> JSONResponse:
        log.warning("banco indisponível (%s)", erro)
        return resposta_erro(
            503, "INDISPONIVEL", "O catálogo está temporariamente fora do ar. Tente de novo em instantes."
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        codigo = _CODIGO_POR_STATUS.get(erro.status_code, "ERRO")
        mensagem = "Rota não encontrada." if erro.status_code == 404 else "Requisição recusada."
        return resposta_erro(erro.status_code, codigo, mensagem, headers=getattr(erro, "headers", None))

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, erro: Exception) -> JSONResponse:
        log.error("erro inesperado: %s", type(erro).__name__)
        return resposta_erro(500, "ERRO_INTERNO", "Erro inesperado. Tente de novo em instantes.")
