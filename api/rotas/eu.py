"""Área do autor (US-15): `/eu`, "Meus anúncios" e a classificação da mensagem retida.

As duas exceções da invariante 5 vivem só aqui, e só para a própria pessoa:
- a mensagem retida que ABRIU uma thread dela (`fora_do_catalogo: true`, com o motivo);
- o item que ela ocultou (`oculto: true`).
A pessoa é sempre o e-mail da sessão, comparado no SQL com o remetente ou o `autor_email`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api import banco, erros, respostas, sessao
from api.rotas.itens import TIPOS, detalhe_para_resposta

roteador = APIRouter()

FONTE_CLASSIFICACAO = "classificação pelo autor"


def exigir_sessao(request: Request) -> sessao.Sessao:
    atual = sessao.ler(request)
    if atual is None:
        raise erros.nao_autenticado()
    return atual


@roteador.get("/eu")
def obter_sessao(request: Request) -> dict:
    atual = exigir_sessao(request)
    # Nunca o e-mail (invariante 1): só o nome que o Google devolveu.
    return {"autenticado": True, "nome": atual.nome}


@roteador.get("/eu/itens")
def listar_meus_itens(request: Request) -> list[dict]:
    atual = exigir_sessao(request)
    with request.app.state.banco.conexao() as con:
        itens = [respostas.item_do_autor(l) for l in banco.itens_do_autor(con, atual.email)]
        retidas = [respostas.retida_do_autor(l) for l in banco.retidas_do_autor(con, atual.email)]
    # Uma lista só, do registro mais recente para o mais antigo.
    return sorted(itens + retidas, key=lambda r: r["data_registro"] or "", reverse=True)


async def _tipo_do_corpo(request: Request) -> str:
    try:
        corpo = await request.json()
    except ValueError:
        corpo = None
    tipo = corpo.get("tipo") if isinstance(corpo, dict) else None
    if tipo not in TIPOS or (isinstance(corpo, dict) and set(corpo) - {"tipo"}):
        # O contrato prevê 422 para tipo inválido nesta rota.
        raise erros.ErroApi(422, "PARAMETROS_INVALIDOS", "Informe `tipo`: perdido ou achado.")
    return tipo


@roteador.post("/eu/retidas/{id}/classificar", status_code=201)
async def classificar_retida(request: Request, id: str) -> JSONResponse:
    atual = exigir_sessao(request)
    numero = respostas.numero_do_id(id, respostas.PADRAO_ID_RETIDA)
    if numero is None:
        raise erros.nao_encontrado()
    tipo = await _tipo_do_corpo(request)

    with request.app.state.banco.conexao() as con, con.transaction():
        retida = banco.retida_do_autor(con, numero, atual.email)
        if retida is None:
            # Retida de outra pessoa é 404, como se não existisse (decisão do PO em 28/10/2026).
            raise erros.nao_encontrado()
        if retida["resolvida"] or banco.thread_tem_item(con, retida["thread_id"]):
            raise erros.ErroApi(409, "JA_CLASSIFICADA", "Esta mensagem já virou item.")

        item_id = banco.criar_item_da_retida(
            con,
            tipo=tipo,
            thread_id=retida["thread_id"],
            autor_email=atual.email,
            descricao=respostas.assunto_limpo(retida["assunto"])
            or " ".join((retida["corpo"] or "").split())[: respostas.TAMANHO_TRECHO_RETIDA],
            data_anuncio=retida["data_envio"],
        )
        banco.registrar_evento(
            con, item_id, "classificacao_pelo_autor", FONTE_CLASSIFICACAO, aplicado=True,
            situacao_nova="aberto",
            detalhes={"retida": respostas.id_retida(numero), "tipo": tipo},
        )
        banco.resolver_retida(con, numero, retida["mensagem_id"])

    return JSONResponse(detalhe_para_resposta(request, item_id, atual, incluir_oculto=False), status_code=201)
