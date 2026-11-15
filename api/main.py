"""Aplicação FastAPI: monta as rotas sob API_PREFIX (/api) e os tratadores de erro.

Rodar: `uvicorn api.main:app --reload --port 8000` a partir da raiz do repositório.
A API é a única porta do site para os dados (invariante 8): ela não chama o worker e o worker
não a chama. O banco é o único ponto de encontro.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request

from api import config as modulo_config
from api import erros, privacidade
from api.banco import Banco
from api.rotas import itens, locais

log_acesso = logging.getLogger("api.acesso")


def criar_app(config: modulo_config.Config | None = None) -> FastAPI:
    privacidade.instalar_mascara_de_logs()
    config = config or modulo_config.carregar()
    banco = Banco(config.database_url, timeout=config.banco_timeout)

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        banco.abrir()
        yield
        banco.fechar()

    # Sem /docs nem /openapi.json gerados: o contrato oficial é shared/openapi.yaml.
    app = FastAPI(
        title="API Achados e Perdidos CIn-UFPE",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=ciclo_de_vida,
    )
    app.state.config = config
    app.state.banco = banco
    erros.instalar(app)

    @app.middleware("http")
    async def registrar_acesso(request: Request, chamar_proximo):
        inicio = time.perf_counter()
        resposta = await chamar_proximo(request)
        caminho = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        # A query pode trazer um endereço (busca, retorno): a fábrica de logs o mascara.
        log_acesso.info(
            "%s %s %s %.0fms", request.method, caminho, resposta.status_code,
            (time.perf_counter() - inicio) * 1000,
        )
        return resposta

    api = APIRouter(prefix=config.api_prefix)
    api.include_router(itens.roteador)
    api.include_router(locais.roteador)
    app.include_router(api)
    return app


def __getattr__(nome: str):
    # `uvicorn api.main:app` cria a aplicação só quando é pedida, para os testes poderem
    # importar este módulo sem um .env completo.
    if nome == "app":
        aplicacao = criar_app()
        globals()["app"] = aplicacao
        return aplicacao
    raise AttributeError(nome)
