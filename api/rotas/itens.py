"""Rotas de itens do catálogo.

Leitura pública (US-04, US-05): `GET /itens` e `GET /itens/{id}`. A visibilidade é decidida
aqui, no servidor (invariante 5): oculto, retido ou inexistente é sempre o mesmo 404.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from api import banco, erros, privacidade, respostas, sessao

roteador = APIRouter()

TIPOS = ("perdido", "achado")
SITUACOES = ("aberto", "reivindicado", "encerrado")
LIMITE_PADRAO = 20
LIMITE_MAXIMO = 100


def _inteiro(valor: str | None, padrao: int, minimo: int, maximo: int | None, nome: str) -> int:
    if valor is None or valor == "":
        return padrao
    if not (valor.isascii() and valor.isdigit()) or len(valor) > 9:
        raise erros.parametros_invalidos(f"`{nome}` precisa ser um número inteiro.")
    numero = int(valor)
    if numero < minimo or (maximo is not None and numero > maximo):
        limites = f"entre {minimo} e {maximo}" if maximo else f"a partir de {minimo}"
        raise erros.parametros_invalidos(f"`{nome}` precisa estar {limites}.")
    return numero


def _vocabulario(valor: str | None, aceitos: tuple[str, ...], nome: str) -> str | None:
    if valor is None or valor == "":
        return None
    if valor not in aceitos:
        raise erros.parametros_invalidos(f"`{nome}` aceita só: {', '.join(aceitos)}.")
    return valor


@roteador.get("/itens")
def listar_itens(
    request: Request,
    texto: str | None = None,
    local: str | None = None,
    situacao: str | None = None,
    tipo: str | None = None,
    pagina: str | None = None,
    limite: str | None = None,
) -> dict:
    filtros = banco.FiltrosCatalogo(
        texto=(texto or "").strip() or None,
        local=(local or "").strip() or None,
        situacao=_vocabulario(situacao, SITUACOES, "situacao"),
        tipo=_vocabulario(tipo, TIPOS, "tipo"),
    )
    numero_pagina = _inteiro(pagina, 1, 1, None, "pagina")
    tamanho = _inteiro(limite, LIMITE_PADRAO, 1, LIMITE_MAXIMO, "limite")
    com_sessao = sessao.ler(request) is not None

    with request.app.state.banco.conexao() as con:
        linhas, total = banco.itens_publicados(con, filtros, numero_pagina, tamanho, com_sessao)

    return {
        "itens": [respostas.item_resumo(linha) for linha in linhas],
        "paginacao": respostas.paginacao(numero_pagina, tamanho, total),
    }


def carregar_item_publicado(request: Request, id: str, email_sessao: str | None) -> dict:
    numero = respostas.numero_do_id(id)
    if numero is None:
        raise erros.nao_encontrado()
    with request.app.state.banco.conexao() as con:
        linha = banco.item_publicado(con, numero, email_sessao)
    if linha is None:
        raise erros.nao_encontrado()
    return linha


def texto_original(request: Request, linha: dict, atual: sessao.Sessao | None) -> str | None:
    """Corpo da mensagem que abriu a thread, mascarado, só para quem entrou (US-04, US-05).

    Sem sessão é sempre `null`: o texto nem é lido do banco. Item cadastrado pelo site não
    tem mensagem de origem, então também é `null`.
    """
    if atual is None or linha.get("origem") != "lista" or not linha.get("thread_id"):
        return None
    with request.app.state.banco.conexao() as con:
        abertura = banco.mensagem_de_abertura(con, linha["thread_id"])
    if abertura is None:
        return None
    return privacidade.mascarar(abertura["corpo"])


@roteador.get("/itens/{id}")
def obter_item(request: Request, id: str) -> dict:
    atual = sessao.ler(request)
    linha = carregar_item_publicado(request, id, atual.email if atual else None)
    return respostas.item_detalhe(linha, texto_original(request, linha, atual))
