"""Envio de e-mail privado pela conta do projeto (ADR-011), atrás de uma interface com três modos.

- `nao_enviar`: não envia nada (padrão em desenvolvimento).
- `arquivo`: grava a mensagem como `.eml` em `EMAIL_ARQUIVO_DIR` (para conferir o que sairia).
- `smtp`: envia pela conta Gmail do projeto com senha de app. **Nunca** em desenvolvimento nem
  em teste.

O sistema nunca posta na lista. Nenhum modo escreve endereço no log.
"""

from __future__ import annotations

import logging
import secrets
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from api.config import Config

log = logging.getLogger("api.envio")


class FalhaEnvio(RuntimeError):
    """A mensagem não saiu. A API responde 502 ENVIO_FALHOU."""


@dataclass(frozen=True)
class Mensagem:
    remetente: str
    destinatario: str
    responder_para: str
    assunto: str
    corpo: str

    def como_email(self) -> EmailMessage:
        email = EmailMessage()
        email["From"] = self.remetente
        email["To"] = self.destinatario
        email["Reply-To"] = self.responder_para
        email["Subject"] = self.assunto
        email["Date"] = formatdate(localtime=False)
        email["Message-ID"] = make_msgid(domain="achados-perdidos.invalid")
        email.set_content(self.corpo)
        return email


class NaoEnviar:
    modo = "nao_enviar"

    def enviar(self, mensagem: Mensagem) -> None:
        log.info("envio desligado (EMAIL_MODO_ENVIO=nao_enviar): mensagem descartada")


class GravarEmArquivo:
    modo = "arquivo"

    def __init__(self, pasta: str) -> None:
        self.pasta = Path(pasta)

    def enviar(self, mensagem: Mensagem) -> Path:
        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            arquivo = self.pasta / f"{carimbo}-{secrets.token_hex(4)}.eml"
            arquivo.write_bytes(bytes(mensagem.como_email()))
        except OSError as erro:
            raise FalhaEnvio(type(erro).__name__) from None
        log.info("mensagem gravada em arquivo (%s)", arquivo.name)
        return arquivo


class EnviarPorSmtp:
    modo = "smtp"

    def __init__(self, host: str, porta: int, usuario: str, senha: str) -> None:
        self.host, self.porta, self.usuario, self._senha = host, porta, usuario, senha

    def enviar(self, mensagem: Mensagem) -> None:
        try:
            with smtplib.SMTP(self.host, self.porta, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(self.usuario, self._senha)
                smtp.send_message(mensagem.como_email())
        except (smtplib.SMTPException, OSError) as erro:
            log.warning("envio por SMTP falhou (%s)", type(erro).__name__)
            raise FalhaEnvio(type(erro).__name__) from None
        log.info("mensagem enviada por SMTP")


def criar(config: Config):
    if config.email_modo_envio == "smtp":
        return EnviarPorSmtp(config.smtp_host, config.smtp_port, config.smtp_usuario, config.smtp_senha)
    if config.email_modo_envio == "arquivo":
        return GravarEmArquivo(config.email_arquivo_dir)
    return NaoEnviar()
