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


# ---------------------------------------------------------------------------
# Ações do autor (US-15): corrigir, encerrar, ocultar
# ---------------------------------------------------------------------------

LOCALIZACOES = ("no local", "com quem achou", "com um setor", "caixa do bloco A/E", "devolvido")
FONTE_AUTOR = "confirmação do autor"
CAMPOS_EDITAVEIS = ("descricao", "local", "localizacao", "setor")


def detalhe_para_resposta(
    request: Request, item_id: int, atual: sessao.Sessao | None, incluir_oculto: bool
) -> dict:
    with request.app.state.banco.conexao() as con:
        linha = banco.item_por_id(con, item_id, atual.email if atual else None, incluir_oculto=incluir_oculto)
    return respostas.item_detalhe(linha, texto_original(request, linha, atual))


def _exigir_sessao(request: Request) -> sessao.Sessao:
    atual = sessao.ler(request)
    if atual is None:
        raise erros.nao_autenticado()
    return atual


def _item_do_autor(con, numero: int | None, atual: sessao.Sessao, aceitar_oculto: bool = False) -> dict:
    """Trava o item para alteração. Oculto ou inexistente é 404; de outra pessoa, 403.

    A autoria vem sempre do e-mail da sessão, comparado no SQL, nunca de campo do corpo.
    """
    if numero is None:
        raise erros.nao_encontrado()
    linha = banco.item_por_id(con, numero, atual.email, incluir_oculto=True, travar=True)
    if linha is None:
        raise erros.nao_encontrado()
    if linha["oculto"] and not (aceitar_oculto and linha["pode_gerir"]):
        raise erros.nao_encontrado()
    if not linha["pode_gerir"]:
        raise erros.nao_autorizado()
    return linha


def _texto(valor, nome: str, minimo: int = 1) -> str:
    if not isinstance(valor, str) or len(valor.strip()) < minimo:
        raise erros.parametros_invalidos(f"`{nome}` precisa de pelo menos {minimo} caractere(s).")
    return valor.strip()


def validar_edicao(corpo, tipo_item: str) -> dict:
    """Valida o corpo do PATCH contra `AtualizarItemRequisicao`. Devolve só os campos enviados."""
    if not isinstance(corpo, dict) or not corpo:
        raise erros.parametros_invalidos("Envie ao menos um campo: descricao, local, localizacao ou setor.")
    fora = set(corpo) - set(CAMPOS_EDITAVEIS)
    if fora:
        raise erros.parametros_invalidos("Só dá para corrigir descricao, local, localizacao e setor.")
    campos: dict = {}
    if "descricao" in corpo:
        campos["descricao"] = _texto(corpo["descricao"], "descricao")
    if "local" in corpo:
        local = corpo["local"]
        if not isinstance(local, list) or not local:
            raise erros.parametros_invalidos("`local` precisa ser uma lista com pelo menos um local.")
        campos["local"] = [_texto(nome, "local") for nome in local]
    if "localizacao" in corpo:
        if corpo["localizacao"] not in LOCALIZACOES:
            raise erros.parametros_invalidos("`localizacao` fora do vocabulário.")
        if tipo_item == "perdido":
            # Na perda a localização atual não existe: quem perdeu não sabe onde o objeto está.
            raise erros.parametros_invalidos("Item perdido não tem `localizacao`.")
        campos["localizacao"] = corpo["localizacao"]
    if "setor" in corpo:
        if corpo["setor"] is not None and not isinstance(corpo["setor"], str):
            raise erros.parametros_invalidos("`setor` precisa ser texto.")
        campos["setor"] = (corpo["setor"] or "").strip() or None
    return campos


async def _json(request: Request):
    try:
        return await request.json()
    except ValueError:
        raise erros.parametros_invalidos("Corpo da requisição não é JSON.") from None


@roteador.patch("/itens/{id}")
async def editar_item(request: Request, id: str) -> dict:
    atual = _exigir_sessao(request)
    numero = respostas.numero_do_id(id)
    corpo = await _json(request)

    with request.app.state.banco.conexao() as con, con.transaction():
        linha = _item_do_autor(con, numero, atual)
        pedidos = validar_edicao(corpo, linha["tipo"])

        localizacao_final = pedidos.get("localizacao", linha["localizacao"])
        if localizacao_final != "com um setor":
            # Setor só vale com "com um setor"; mudar a localização descarta o setor anterior.
            pedidos["setor"] = None
        elif "setor" not in pedidos and "localizacao" in pedidos:
            pedidos["setor"] = linha["setor"] if linha["localizacao"] == "com um setor" else None

        antes = {c: linha[c] for c in pedidos}
        mudou = {c: v for c, v in pedidos.items() if (list(v) if isinstance(v, list) else v) != (list(antes[c]) if isinstance(antes[c], list) else antes[c])}
        if mudou:
            banco.atualizar_campos(con, linha["id"], mudou)
            # O valor anterior fica no evento: nada é apagado (invariante 4).
            banco.registrar_evento(
                con, linha["id"], "edicao", FONTE_AUTOR, aplicado=True,
                situacao_anterior=linha["situacao"], situacao_nova=linha["situacao"],
                detalhes={
                    "antes": {c: (list(antes[c]) if isinstance(antes[c], list) else antes[c]) for c in mudou},
                    "depois": mudou,
                },
            )

    return detalhe_para_resposta(request, linha["id"], atual, incluir_oculto=False)


@roteador.post("/itens/{id}/encerrar")
def encerrar_item(request: Request, id: str) -> dict:
    atual = _exigir_sessao(request)
    numero = respostas.numero_do_id(id)

    with request.app.state.banco.conexao() as con, con.transaction():
        linha = _item_do_autor(con, numero, atual)
        anterior = linha["situacao"]
        # A API confere a situação ANTES do UPDATE (invariante 2); o trigger é só rede.
        if anterior in ("aberto", "reivindicado"):
            banco.encerrar(con, linha["id"])
            banco.registrar_evento(
                con, linha["id"], "desfecho", FONTE_AUTOR, aplicado=True,
                situacao_anterior=anterior, situacao_nova="encerrado",
            )
        else:
            banco.registrar_evento(
                con, linha["id"], "desfecho", FONTE_AUTOR, aplicado=False,
                situacao_anterior=anterior, situacao_nova="encerrado",
                motivo_recusa="item já estava encerrado",
            )

    return detalhe_para_resposta(request, linha["id"], atual, incluir_oculto=False)


@roteador.post("/itens/{id}/ocultar")
def ocultar_item(request: Request, id: str) -> dict:
    atual = _exigir_sessao(request)
    numero = respostas.numero_do_id(id)

    with request.app.state.banco.conexao() as con, con.transaction():
        linha = _item_do_autor(con, numero, atual, aceitar_oculto=True)
        # Repetir é idempotente: o item já oculto não gera evento novo.
        if not linha["oculto"]:
            banco.ocultar(con, linha["id"])
            banco.registrar_evento(
                con, linha["id"], "ocultacao", FONTE_AUTOR, aplicado=True,
                situacao_anterior=linha["situacao"], situacao_nova=linha["situacao"],
            )

    return detalhe_para_resposta(request, linha["id"], atual, incluir_oculto=True)
