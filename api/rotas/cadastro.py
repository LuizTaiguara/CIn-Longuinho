"""Cadastro pelo site (US-06) e foto do anúncio.

O item cadastrado pelo site já nasce estruturado: publica na hora, sem classificação, com o
autor igual ao e-mail da sessão e um código `AP-XXXXXX` que liga o e-mail pronto (US-07) ao
item quando o worker o ler na lista.
"""

from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.datastructures import UploadFile

from api import banco, erros, fotos, sessao
from api.rotas.itens import LOCALIZACOES, TIPOS, _exigir_sessao, _item_do_autor, _json, detalhe_para_resposta
from api import respostas

roteador = APIRouter()

FONTE_SITE = "cadastro pelo site"
FONTE_AUTOR = "confirmação do autor"
ALFABETO_CODIGO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
TAMANHO_MINIMO_DESCRICAO = 5


def novo_codigo() -> str:
    """`AP-` + 6 caracteres de A-Z e 2-7 (base32), sorteados com `secrets`."""
    return "AP-" + "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))


def _codigo_livre(con) -> str:
    for _ in range(20):
        codigo = novo_codigo()
        if not banco.codigo_existe(con, codigo):
            return codigo
    raise RuntimeError("não foi possível sortear um código livre")  # 32^6 ≈ 1 bilhão


def validar_cadastro(corpo) -> dict:
    """Valida `NovoItemRequisicao`. A mensagem de erro nomeia o campo, para o site mostrar junto dele."""
    if not isinstance(corpo, dict):
        raise erros.parametros_invalidos("Envie tipo, descricao e local.")
    tipo = corpo.get("tipo")
    if tipo not in TIPOS:
        raise erros.parametros_invalidos("`tipo`: escolha achado ou perdido.")
    descricao = corpo.get("descricao")
    if not isinstance(descricao, str) or len(descricao.strip()) < TAMANHO_MINIMO_DESCRICAO:
        raise erros.parametros_invalidos(
            f"`descricao`: escreva pelo menos {TAMANHO_MINIMO_DESCRICAO} caracteres."
        )
    local = corpo.get("local")
    if (
        not isinstance(local, list)
        or not local
        or not all(isinstance(nome, str) and nome.strip() for nome in local)
    ):
        raise erros.parametros_invalidos("`local`: escolha pelo menos um local.")
    # Valores fora da tabela `local` são aceitos: é a opção "outro" do formulário.
    locais = list(dict.fromkeys(nome.strip() for nome in local))

    localizacao = setor = None
    if tipo == "achado":
        localizacao = corpo.get("localizacao")
        if localizacao is None or localizacao == "":
            raise erros.ErroApi(
                400, "LOCALIZACAO_OBRIGATORIA", "`localizacao`: diga onde o objeto está agora."
            )
        if localizacao not in LOCALIZACOES:
            raise erros.parametros_invalidos("`localizacao` fora do vocabulário.")
        if localizacao == "com um setor":
            valor = corpo.get("setor")
            if valor is not None and not isinstance(valor, str):
                raise erros.parametros_invalidos("`setor` precisa ser texto.")
            setor = (valor or "").strip() or None
    # Na perda, localização e setor são ignorados: quem perdeu não sabe onde o objeto está.
    return {
        "tipo": tipo,
        "descricao": descricao.strip(),
        "local": locais,
        "localizacao": localizacao,
        "setor": setor,
    }


@roteador.post("/itens", status_code=201)
async def cadastrar_item(request: Request) -> JSONResponse:
    atual = _exigir_sessao(request)
    dados = validar_cadastro(await _json(request))

    with request.app.state.banco.conexao() as con, con.transaction():
        banco.travar_cadastros_do_autor(con, atual.email)
        # Clique duplo: o mesmo cadastro da mesma pessoa em menos de 30 s devolve o mesmo item.
        item_id = banco.cadastro_recente_igual(con, atual.email, dados["tipo"], dados["descricao"])
        if item_id is None:
            item_id = banco.criar_item_do_site(
                con, codigo=_codigo_livre(con), autor_email=atual.email, **dados
            )
            banco.registrar_evento(
                con, item_id, "criacao", FONTE_SITE, aplicado=True, situacao_nova="aberto"
            )

    return JSONResponse(detalhe_para_resposta(request, item_id, atual, incluir_oculto=False), status_code=201)


async def _ler_foto(request: Request) -> bytes:
    tamanho = request.headers.get("content-length")
    if tamanho and tamanho.isdigit() and int(tamanho) > fotos.LIMITE_BYTES + 64 * 1024:
        raise erros.ErroApi(413, "FOTO_GRANDE", "A foto passa de 5 MB. Envie uma menor.")
    try:
        formulario = await request.form(max_files=1, max_fields=4)
    except Exception:
        raise erros.ErroApi(400, "FOTO_INVALIDA", "Envie a foto no campo `foto` (multipart).") from None
    arquivo = formulario.get("foto")
    if not isinstance(arquivo, UploadFile):
        raise erros.ErroApi(400, "FOTO_INVALIDA", "Envie a foto no campo `foto` (multipart).")
    conteudo = await arquivo.read(fotos.LIMITE_BYTES + 1)
    await formulario.close()
    return conteudo


@roteador.post("/itens/{id}/foto")
async def enviar_foto(request: Request, id: str) -> dict:
    atual = _exigir_sessao(request)
    numero = respostas.numero_do_id(id)
    config = request.app.state.config

    # Autoria antes de ler o arquivo: quem não pode gerir nem chega a enviar bytes ao disco.
    with request.app.state.banco.conexao() as con:
        _item_do_autor(con, numero, atual)

    conteudo = await _ler_foto(request)
    try:
        regravada, extensao = fotos.preparar(conteudo)
    except fotos.FotoGrande:
        raise erros.ErroApi(413, "FOTO_GRANDE", "A foto passa de 5 MB. Envie uma menor.") from None
    except fotos.FotoInvalida:
        raise erros.ErroApi(400, "FOTO_INVALIDA", "Formato não aceito. Envie JPEG, PNG ou WebP.") from None

    nome = fotos.gravar(config.fotos_dir, regravada, extensao)
    foto_url = f"{config.api_prefix}/fotos/{nome}"
    with request.app.state.banco.conexao() as con, con.transaction():
        linha = _item_do_autor(con, numero, atual)
        banco.trocar_foto(con, linha["id"], foto_url)
        # O arquivo anterior fica no disco e a URL anterior fica no evento (nada é apagado).
        banco.registrar_evento(
            con, linha["id"], "edicao", FONTE_AUTOR, aplicado=True,
            situacao_anterior=linha["situacao"], situacao_nova=linha["situacao"],
            detalhes={"antes": {"foto_url": linha["foto_url"]}, "depois": {"foto_url": foto_url}},
        )

    return detalhe_para_resposta(request, linha["id"], atual, incluir_oculto=False)


@roteador.get("/fotos/{nome}")
def obter_foto(request: Request, nome: str) -> FileResponse:
    """Serve a foto em uso por um item visível (ou pelo próprio autor, se o item foi ocultado).

    Foto substituída ou de item oculto devolve 404, como o item.
    """
    config = request.app.state.config
    if not re.match(fotos.PADRAO_NOME, nome):
        raise erros.nao_encontrado()
    atual = sessao.ler(request)
    with request.app.state.banco.conexao() as con:
        dono = banco.item_da_foto(con, f"{config.api_prefix}/fotos/{nome}", atual.email if atual else None)
    if dono is None or (dono["oculto"] and not dono["pode_gerir"]):
        raise erros.nao_encontrado()
    caminho = fotos.Path(config.fotos_dir) / nome
    if not caminho.is_file():
        raise erros.nao_encontrado()
    return FileResponse(
        caminho,
        media_type=fotos.TIPO_POR_EXTENSAO[nome.rsplit(".", 1)[1]],
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )
