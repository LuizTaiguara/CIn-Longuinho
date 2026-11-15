"""Envio de e-mail pela conta do projeto (US-15: aviso ao autor). ADR-003: o envio fica atrás de
uma interface, para o worker rodar sem rede e sem credencial em desenvolvimento e nos testes.

`EMAIL_MODO_ENVIO`:
- `nao_enviar` (padrão): só registra no log, com o endereço mascarado.
- `arquivo`: grava um `.eml` por mensagem em `EMAIL_ARQUIVO_DIR`, para inspeção.
- `smtp`: envia por `SMTP_HOST`/`SMTP_PORT` com `SMTP_USUARIO`/`SMTP_SENHA` (Gmail com senha de
  app). **Nunca roda em teste**: a suíte força `nao_enviar`.

Qualquer modo recusa enviar para a própria lista: o aviso vai só para a pessoa.
"""
import logging
import os
import re
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import List, Mapping, Optional

from worker.registro import mascarar_emails

log = logging.getLogger("worker.envio")

ENDERECO_DA_LISTA = "achados-perdidos@cin.ufpe.br"
MODOS = ("nao_enviar", "arquivo", "smtp")


class EnvioRecusado(Exception):
    """O destinatário não pode receber (lista, vazio ou malformado). Nada foi enviado."""


class EnvioIndisponivel(Exception):
    """O servidor de envio falhou. Nada foi enviado; dá para tentar no próximo ciclo."""


@dataclass(frozen=True)
class EmailSaida:
    para: str
    assunto: str
    corpo: str


_ENDERECO = re.compile(r"^[^@\s<>,]+@[^@\s<>,]+\.[^@\s<>,]+$")


def conferir_destinatario(para: str) -> str:
    endereco = (para or "").strip().lower()
    if not _ENDERECO.match(endereco):
        raise EnvioRecusado("destinatário vazio ou malformado")
    if endereco == ENDERECO_DA_LISTA:
        raise EnvioRecusado("o aviso nunca vai para a lista")
    return endereco


class Envio(ABC):
    def __init__(self, remetente: str):
        self.remetente = remetente

    def enviar(self, email: EmailSaida) -> None:
        """Confere o destinatário e entrega. Exceções: EnvioRecusado, EnvioIndisponivel."""
        para = conferir_destinatario(email.para)
        self._entregar(self._montar(para, email))

    def _montar(self, para: str, email: EmailSaida) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.remetente
        msg["To"] = para
        msg["Subject"] = email.assunto
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=(self.remetente.rsplit("@", 1)[-1] or "longuinho.invalid"))
        msg.set_content(email.corpo)
        return msg

    @abstractmethod
    def _entregar(self, msg: EmailMessage) -> None: ...


class NaoEnviar(Envio):
    """Desenvolvimento e testes. Guarda o que teria enviado em `self.enviados`."""

    def __init__(self, remetente: str = ""):
        super().__init__(remetente)
        self.enviados: List[EmailMessage] = []

    def _entregar(self, msg: EmailMessage) -> None:
        self.enviados.append(msg)
        log.info("envio desligado (nao_enviar): teria enviado %r para %s", msg["Subject"], mascarar_emails(msg["To"]))


class ParaArquivo(Envio):
    def __init__(self, remetente: str, diretorio: str):
        super().__init__(remetente)
        self.diretorio = Path(diretorio)

    def _entregar(self, msg: EmailMessage) -> None:
        try:
            self.diretorio.mkdir(parents=True, exist_ok=True)
            carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            (self.diretorio / f"{carimbo}.eml").write_bytes(bytes(msg))
        except OSError as erro:
            raise EnvioIndisponivel(f"não consegui gravar em {self.diretorio}: {type(erro).__name__}") from erro


class PorSmtp(Envio):
    def __init__(self, remetente: str, host: str, porta: int, usuario: str, senha: str):
        super().__init__(remetente)
        self.host, self.porta, self.usuario, self.senha = host, porta, usuario, senha

    def _entregar(self, msg: EmailMessage) -> None:
        try:
            with smtplib.SMTP(self.host, self.porta, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.usuario, self.senha)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as erro:
            raise EnvioIndisponivel(f"SMTP falhou: {type(erro).__name__}") from erro


def criar_envio(ambiente: Optional[Mapping[str, str]] = None) -> Envio:
    env = os.environ if ambiente is None else ambiente
    modo = (env.get("EMAIL_MODO_ENVIO") or "nao_enviar").strip().lower()
    remetente = env.get("EMAIL_REMETENTE", "")
    if modo == "nao_enviar":
        return NaoEnviar(remetente)
    if modo == "arquivo":
        return ParaArquivo(remetente, env.get("EMAIL_ARQUIVO_DIR", "./dados/emails-enviados"))
    if modo == "smtp":
        faltando = [v for v in ("EMAIL_REMETENTE", "SMTP_HOST", "SMTP_USUARIO", "SMTP_SENHA") if not env.get(v)]
        if faltando:
            raise ValueError(f"EMAIL_MODO_ENVIO=smtp sem {', '.join(faltando)}")
        return PorSmtp(remetente, env["SMTP_HOST"], int(env.get("SMTP_PORT", "587")), env["SMTP_USUARIO"], env["SMTP_SENHA"])
    raise ValueError(f"EMAIL_MODO_ENVIO inválido: {modo!r}. Use {', '.join(MODOS)}.")
