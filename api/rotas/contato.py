"""Falar com quem anunciou sem ver o endereço (US-05, ADR-011).

A mensagem sai da conta do projeto para o autor do item, com o endereço da sessão em `Reply-To`.
Quem escreve nunca vê o endereço do autor: ele não sai na resposta, no erro, no log nem no evento.
A exigência de sessão do CIn é o freio contra spam.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from api import banco, envio, erros, privacidade, respostas
from api.rotas.cadastro import descricao_curta
from api.rotas.itens import _exigir_sessao, _json

roteador = APIRouter()

FONTE_CONTATO = "terceiro"
TAMANHO_MINIMO = 10
TAMANHO_MAXIMO = 2000
REMETENTE_PADRAO = "remetente-nao-configurado@exemplo.invalid"  # só nos modos sem envio real


def validar_mensagem(corpo) -> str:
    mensagem = corpo.get("mensagem") if isinstance(corpo, dict) else None
    if not isinstance(mensagem, str):
        raise erros.parametros_invalidos("`mensagem`: escreva a mensagem para quem anunciou.")
    mensagem = mensagem.strip()
    if len(mensagem) < TAMANHO_MINIMO:
        raise erros.parametros_invalidos(f"`mensagem`: escreva pelo menos {TAMANHO_MINIMO} caracteres.")
    if len(mensagem) > TAMANHO_MAXIMO:
        raise erros.parametros_invalidos(f"`mensagem`: use no máximo {TAMANHO_MAXIMO} caracteres.")
    return mensagem


def montar_contato(item: dict, mensagem: str, nome_sessao: str, site_url: str) -> tuple[str, str]:
    """(assunto, corpo). O corpo não traz endereço de ninguém: o de quem escreveu vai só no Reply-To."""
    descricao = privacidade.mascarar(item["descricao"]) or ""
    quem = nome_sessao.strip() or "Uma pessoa"
    corpo = "\n".join([
        f"{quem} entrou com a conta do CIn e escreveu sobre o seu anúncio no catálogo de Achados e",
        "Perdidos do CIn:",
        "",
        f"  {descricao_curta(descricao)}",
        f"  {site_url}/itens/{respostas.id_item(item['id'])}",
        "",
        "----- mensagem -----",
        mensagem,
        "--------------------",
        "",
        "Para responder, é só responder a este e-mail: a resposta vai direto para essa pessoa,",
        "não para a lista nem para o projeto. Seu endereço não foi mostrado a ela; se você",
        "responder, ela passa a ver o seu endereço.",
        "",
        "Este e-mail foi enviado pelo catálogo de Achados e Perdidos do CIn.",
    ])
    assunto = f"[Achados e Perdidos] Sobre o seu anúncio: {descricao_curta(descricao)}"
    return assunto, corpo + "\n"


@roteador.post("/itens/{id}/contato", status_code=202)
async def contatar_autor(request: Request, id: str) -> Response:
    atual = _exigir_sessao(request)
    numero = respostas.numero_do_id(id)
    mensagem = validar_mensagem(await _json(request))
    if numero is None:
        raise erros.nao_encontrado()
    config = request.app.state.config

    with request.app.state.banco.conexao() as con:
        item = banco.destinatario_do_contato(con, numero)
    if item is None:
        raise erros.nao_encontrado()
    destinatario = (item["destinatario"] or "").strip()
    if "@" not in destinatario:
        raise erros.ErroApi(
            502, "ENVIO_FALHOU",
            "Este anúncio não tem um endereço para contato. Responda na conversa da lista.",
        )

    assunto, corpo = montar_contato(item, mensagem, atual.nome, config.site_url)
    try:
        request.app.state.envio.enviar(envio.Mensagem(
            remetente=config.email_remetente or REMETENTE_PADRAO,
            destinatario=destinatario,
            responder_para=atual.email,
            assunto=assunto,
            corpo=corpo,
        ))
    except (envio.FalhaEnvio, ValueError):
        raise erros.ErroApi(
            502, "ENVIO_FALHOU", "Não foi possível enviar a mensagem agora. Tente mais tarde."
        ) from None

    # Só depois do envio: o evento diz que houve contato, nunca de quem nem para quem.
    with request.app.state.banco.conexao() as con, con.transaction():
        banco.registrar_evento(
            con, item["id"], "contato", FONTE_CONTATO, aplicado=True,
            detalhes={"tamanho": len(mensagem)},
        )
    return Response(status_code=202)
