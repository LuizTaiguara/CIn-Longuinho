"""Login com a conta Google do CIn (ADR-010, ADR-011).

O app OAuth é Externo e pede só identidade (`openid email profile`). O parâmetro `hd` é só
dica de interface: quem confere o domínio e o `email_verified` é o servidor, em
`rotas/auth.py`, depois de verificar a assinatura do `id_token` com `google-auth`.

Os testes trocam `app.state.google` por um falso: nada aqui roda sem internet.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from api.config import Config

URL_AUTORIZACAO = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"
ESCOPOS = "openid email profile"


class FalhaGoogle(RuntimeError):
    """O Google não respondeu, recusou o código ou devolveu um token inválido."""


class ClienteGoogle:
    def __init__(self, config: Config) -> None:
        self._config = config

    @property
    def configurado(self) -> bool:
        return bool(self._config.google_client_id and self._config.google_client_secret)

    def url_autorizacao(self, estado: str) -> str:
        parametros = {
            "client_id": self._config.google_client_id,
            "redirect_uri": self._config.redirect_uri_google,
            "response_type": "code",
            "scope": ESCOPOS,
            "state": estado,
            "hd": self._config.dominio_permitido,
            "prompt": "select_account",
        }
        return f"{URL_AUTORIZACAO}?{urlencode(parametros)}"

    def identidade(self, codigo: str) -> dict:
        """Troca o código pelo `id_token` e devolve as declarações já verificadas."""
        # Importados aqui para a API subir mesmo se o login Google não for usado.
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        try:
            resposta = httpx.post(
                URL_TOKEN,
                data={
                    "code": codigo,
                    "client_id": self._config.google_client_id,
                    "client_secret": self._config.google_client_secret,
                    "redirect_uri": self._config.redirect_uri_google,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
            resposta.raise_for_status()
            token = resposta.json()["id_token"]
            return id_token.verify_oauth2_token(token, Request(), self._config.google_client_id)
        except Exception as erro:  # rede, HTTP, JSON, assinatura, audiência, validade
            raise FalhaGoogle(type(erro).__name__) from None
