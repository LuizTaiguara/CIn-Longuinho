"""GET /locais: vocabulário fechado dos espaços do CIn (F-07, SCRUM-64)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api import banco, respostas

roteador = APIRouter()


@roteador.get("/locais")
def listar_locais(request: Request) -> list[dict]:
    with request.app.state.banco.conexao() as con:
        return [respostas.local(linha) for linha in banco.locais_ativos(con)]
