"""Configuração da API, lida só de variáveis de ambiente (invariante 9).

O `.env` da raiz do repositório é carregado se existir, sem sobrescrever o que já está no ambiente.
Nenhum valor secreto tem padrão no código: o que falta impede a API de subir.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
DOMINIO_PADRAO = "cin.ufpe.br"


class ConfiguracaoInvalida(RuntimeError):
    """A API se recusa a subir com esta configuração."""


@dataclass(frozen=True)
class Config:
    database_url: str
    sessao_segredo: str
    api_prefix: str = "/api"
    session_cookie_name: str = "sessao_id"
    dominio_permitido: str = DOMINIO_PADRAO
    login_simulado: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    site_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    fotos_dir: str = "./dados/fotos"
    email_modo_envio: str = "nao_enviar"
    email_arquivo_dir: str = "./dados/emails-enviados"
    email_remetente: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_usuario: str = ""
    smtp_senha: str = field(default="", repr=False)
    # Segundos de espera por uma conexão do pool antes de responder 503.
    banco_timeout: float = 5.0

    def __post_init__(self) -> None:
        validar(self)

    @property
    def cookie_seguro(self) -> bool:
        return self.site_url.lower().startswith("https://")

    @property
    def redirect_uri_google(self) -> str:
        if self.google_redirect_uri:
            return self.google_redirect_uri
        return f"{self.api_url.rstrip('/')}{self.api_prefix}/auth/google/callback"


def validar(config: Config) -> None:
    if not config.database_url:
        raise ConfiguracaoInvalida("DATABASE_URL não está definida.")
    if not config.sessao_segredo:
        raise ConfiguracaoInvalida("SESSAO_SEGREDO não está definido.")
    if not config.api_prefix.startswith("/") or config.api_prefix.endswith("/"):
        raise ConfiguracaoInvalida("API_PREFIX deve começar com / e não terminar com / (ex.: /api).")
    if config.login_simulado:
        if config.cookie_seguro:
            raise ConfiguracaoInvalida(
                "LOGIN_SIMULADO está preenchido e SITE_URL é https: o login simulado é só para "
                "desenvolvimento. Esvazie LOGIN_SIMULADO em produção."
            )
        if not config.login_simulado.lower().endswith("@" + config.dominio_permitido):
            raise ConfiguracaoInvalida(
                f"LOGIN_SIMULADO precisa ser um endereço @{config.dominio_permitido}."
            )
    if config.email_modo_envio not in ("nao_enviar", "arquivo", "smtp"):
        raise ConfiguracaoInvalida("EMAIL_MODO_ENVIO deve ser nao_enviar, arquivo ou smtp.")
    if config.email_modo_envio == "smtp":
        faltando = [
            nome
            for nome, valor in (
                ("EMAIL_REMETENTE", config.email_remetente),
                ("SMTP_HOST", config.smtp_host),
                ("SMTP_USUARIO", config.smtp_usuario),
                ("SMTP_SENHA", config.smtp_senha),
            )
            if not valor or valor.startswith("troque-por") or valor.endswith(".invalid")
        ]
        if faltando:
            raise ConfiguracaoInvalida(
                "EMAIL_MODO_ENVIO=smtp exige " + ", ".join(faltando) + " preenchidos de verdade."
            )


def _carregar_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - python-dotenv está no requirements
        return
    load_dotenv(RAIZ_REPOSITORIO / ".env", override=False)


def carregar(ambiente: dict[str, str] | None = None) -> Config:
    """Monta a configuração a partir do ambiente (ou de um dicionário, nos testes)."""
    if ambiente is None:
        _carregar_dotenv()
        ambiente = dict(os.environ)

    def ler(nome: str, padrao: str = "") -> str:
        return ambiente.get(nome, padrao).strip()

    return Config(
        database_url=ler("DATABASE_URL"),
        sessao_segredo=ler("SESSAO_SEGREDO"),
        api_prefix=ler("API_PREFIX", "/api") or "/api",
        session_cookie_name=ler("SESSION_COOKIE_NAME", "sessao_id") or "sessao_id",
        dominio_permitido=(ler("ALLOWED_EMAIL_DOMAIN", DOMINIO_PADRAO) or DOMINIO_PADRAO).lower(),
        login_simulado=ler("LOGIN_SIMULADO"),
        google_client_id=ler("GOOGLE_CLIENT_ID"),
        google_client_secret=ler("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=ler("GOOGLE_REDIRECT_URI"),
        site_url=ler("SITE_URL", "http://localhost:5173").rstrip("/"),
        api_url=ler("API_URL", "http://localhost:8000").rstrip("/"),
        fotos_dir=ler("FOTOS_DIR", "./dados/fotos"),
        email_modo_envio=ler("EMAIL_MODO_ENVIO", "nao_enviar") or "nao_enviar",
        email_arquivo_dir=ler("EMAIL_ARQUIVO_DIR", "./dados/emails-enviados"),
        email_remetente=ler("EMAIL_REMETENTE"),
        smtp_host=ler("SMTP_HOST"),
        smtp_port=int(ler("SMTP_PORT", "587") or "587"),
        smtp_usuario=ler("SMTP_USUARIO"),
        smtp_senha=ler("SMTP_SENHA"),
        banco_timeout=float(ler("BANCO_TIMEOUT", "5") or "5"),
    )
