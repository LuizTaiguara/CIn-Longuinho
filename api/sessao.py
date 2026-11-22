"""Sessão do CIn em cookie assinado (itsdangerous), sem tabela de sessão (ADR-010).

O cookie guarda `{email, nome}` assinado e com carimbo de tempo; vale 7 dias. É `HttpOnly`,
`SameSite=Lax` e `Secure` quando o site é servido por https. O e-mail fica só no cookie da
própria pessoa: nenhuma resposta da API o devolve (invariante 1).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from api.config import Config

DURACAO_SEGUNDOS = 7 * 24 * 60 * 60
_SAL = "longuinho.sessao"


@dataclass(frozen=True)
class Sessao:
    email: str
    nome: str


def _serializador(config: Config) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(config.sessao_segredo, salt=_SAL)


def email_do_dominio(email: str, config: Config) -> bool:
    return email.strip().lower().endswith("@" + config.dominio_permitido)


def assinar(config: Config, email: str, nome: str) -> str:
    return _serializador(config).dumps({"email": email.strip().lower(), "nome": nome})


def ler(request: Request) -> Sessao | None:
    config: Config = request.app.state.config
    valor = request.cookies.get(config.session_cookie_name)
    if not valor:
        return None
    try:
        dados = _serializador(config).loads(valor, max_age=DURACAO_SEGUNDOS)
    except BadSignature:  # inclui SignatureExpired
        return None
    if not isinstance(dados, dict):
        return None
    email = str(dados.get("email") or "")
    # Defesa em profundidade: mesmo com assinatura válida, só conta do CIn é sessão.
    if not email or not email_do_dominio(email, config):
        return None
    return Sessao(email=email.lower(), nome=str(dados.get("nome") or ""))


def gravar(response: Response, config: Config, email: str, nome: str) -> None:
    response.set_cookie(
        config.session_cookie_name,
        assinar(config, email, nome),
        max_age=DURACAO_SEGUNDOS,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.cookie_seguro,
    )


def limpar(response: Response, config: Config) -> None:
    response.delete_cookie(
        config.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.cookie_seguro,
    )
