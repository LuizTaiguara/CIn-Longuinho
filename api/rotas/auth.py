"""Login com a conta do CIn, sessão e logout (US-15, ADR-010).

- Sucesso: cookie de sessão e 302 para `SITE_URL + retorno`.
- Qualquer falha: 302 para `SITE_URL/login?erro=<motivo>`, nunca JSON 403. Motivos:
  `conta_fora_do_cin`, `recusado`, `estado_invalido`, `login_indisponivel`.
- `LOGIN_SIMULADO=<email@cin.ufpe.br>` cria a sessão sem Google (só desenvolvimento; a
  configuração recusa subir com ele se o site for https).
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer

from api import erros, sessao
from api.config import Config
from api.google import FalhaGoogle

roteador = APIRouter()
log = logging.getLogger("api.auth")

COOKIE_ESTADO = "oauth_estado"
VALIDADE_ESTADO_SEGUNDOS = 10 * 60
NOME_SIMULADO = "Pessoa de Teste"


def retorno_seguro(retorno: str | None) -> str:
    """Só caminho relativo da própria aplicação. Qualquer outra coisa vira `/` (sem erro)."""
    if not retorno or not retorno.startswith("/") or retorno.startswith("//"):
        return "/"
    if "\\" in retorno or any(ord(c) < 32 or ord(c) == 127 for c in retorno):
        return "/"
    if "://" in retorno.split("?", 1)[0]:
        return "/"
    return retorno


def _serializador_estado(config: Config) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(config.sessao_segredo, salt="longuinho.oauth.estado")


def _para_o_site(config: Config, caminho: str) -> RedirectResponse:
    return RedirectResponse(config.site_url + caminho, status_code=302)


def _falha(config: Config, motivo: str) -> RedirectResponse:
    resposta = _para_o_site(config, "/login?" + urlencode({"erro": motivo}))
    resposta.delete_cookie(COOKIE_ESTADO, path="/", httponly=True, samesite="lax", secure=config.cookie_seguro)
    return resposta


@roteador.get("/auth/google")
def iniciar_login(request: Request, retorno: str | None = None) -> Response:
    config: Config = request.app.state.config
    destino = retorno_seguro(retorno)

    if config.login_simulado:
        resposta = _para_o_site(config, destino)
        sessao.gravar(resposta, config, config.login_simulado, NOME_SIMULADO)
        log.info("sessão simulada criada")
        return resposta

    google = request.app.state.google
    if not google.configurado:
        log.warning("login Google sem GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET")
        return _falha(config, "login_indisponivel")

    # O nonce vai no state assinado e num cookie do navegador: o callback só aceita o state
    # que nasceu neste navegador (evita login forçado por terceiro).
    nonce = secrets.token_urlsafe(24)
    estado = _serializador_estado(config).dumps({"retorno": destino, "nonce": nonce})
    resposta = RedirectResponse(google.url_autorizacao(estado), status_code=302)
    resposta.set_cookie(
        COOKIE_ESTADO, nonce, max_age=VALIDADE_ESTADO_SEGUNDOS, path="/",
        httponly=True, samesite="lax", secure=config.cookie_seguro,
    )
    return resposta


@roteador.get("/auth/google/callback")
def retorno_login(
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
) -> Response:
    config: Config = request.app.state.config
    try:
        dados = _serializador_estado(config).loads(state or "", max_age=VALIDADE_ESTADO_SEGUNDOS)
    except BadSignature:
        return _falha(config, "estado_invalido")
    nonce = request.cookies.get(COOKIE_ESTADO)
    if not isinstance(dados, dict) or not nonce or not secrets.compare_digest(str(dados.get("nonce")), nonce):
        return _falha(config, "estado_invalido")

    if error or not code:
        return _falha(config, "recusado")

    try:
        identidade = request.app.state.google.identidade(code)
    except FalhaGoogle as falha:
        log.warning("login Google falhou (%s)", falha)
        return _falha(config, "login_indisponivel")

    email = str(identidade.get("email") or "").strip().lower()
    verificado = identidade.get("email_verified") in (True, "true")
    # A conferência do domínio é do servidor; o `hd` mandado ao Google é só dica.
    if not email or not verificado or not sessao.email_do_dominio(email, config):
        log.info("login recusado: conta fora do domínio permitido ou não verificada")
        return _falha(config, "conta_fora_do_cin")

    nome = str(identidade.get("name") or identidade.get("given_name") or "").strip()
    resposta = _para_o_site(config, retorno_seguro(dados.get("retorno")))
    resposta.delete_cookie(COOKIE_ESTADO, path="/", httponly=True, samesite="lax", secure=config.cookie_seguro)
    sessao.gravar(resposta, config, email, nome)
    log.info("sessão criada")
    return resposta


@roteador.post("/auth/logout", status_code=204)
def sair(request: Request) -> Response:
    config: Config = request.app.state.config
    if sessao.ler(request) is None:
        raise erros.nao_autenticado()
    resposta = Response(status_code=204)
    sessao.limpar(resposta, config)
    return resposta
