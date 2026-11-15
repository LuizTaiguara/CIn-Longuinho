"""Aplicação FastAPI: monta as rotas sob API_PREFIX (/api) e os tratadores de erro.

Rodar: `uvicorn api.main:app --reload --port 8000` a partir da raiz do repositório.
A API é a única porta do site para os dados (invariante 8): ela não chama o worker e o worker
não a chama. O banco é o único ponto de encontro.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from api import config as modulo_config
from api import erros
from api.banco import Banco
from api.rotas import itens, locais


def criar_app(config: modulo_config.Config | None = None) -> FastAPI:
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
