"""Fonte Gmail (US-01, ADR-011): lê a conta do projeto, que recebe o encaminhamento da lista.

- OAuth de app instalado, só leitura (`gmail.readonly`). `python -m worker.autorizar_gmail` roda
  uma vez, abre o navegador e grava o token em `GMAIL_TOKEN_FILE`. O JSON do client OAuth fica em
  `GMAIL_PROJECT_CREDENTIALS_FILE`. Nenhum dos dois entra no repositório (invariante 9).
- Baixa cada mensagem no formato `raw` (RFC 822, o mesmo de um .eml) e reaproveita o parser do
  leitor local. `threadId` do Gmail vira `id_conversa`; `Message-ID` vira `id_mensagem`.
- `veio_da_lista` sai só do cabeçalho `X-BeenThere`: resposta direta à conta do projeto (por
  exemplo, ao aviso ao autor) não passou pela lista e fica `ignorada`.
- Nada é marcado na caixa (nem lido, nem etiqueta). O estado vive no banco; a idempotência é pelo
  `Message-ID`. Para não baixar o histórico inteiro a cada ciclo, a consulta usa `after:` com dois
  dias de folga antes da última gravação em `mensagem_bruta`. Banco vazio = histórico inteiro.
- Credencial expirada ou revogada → `CredencialInvalida`; API fora → `FonteIndisponivel`. O ciclo
  encerra e nada é marcado (US-01).
"""
import base64
import email
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email import policy
from pathlib import Path
from typing import Callable, Iterable, Optional

from worker.fonte import CredencialInvalida, FonteIndisponivel, FonteMensagens, MensagemFonte
from worker.leitor_local import interpretar_email

log = logging.getLogger("worker.leitor_gmail")

ESCOPOS = ["https://www.googleapis.com/auth/gmail.readonly"]
LISTA = "achados-perdidos@cin.ufpe.br"
# Fora da consulta: o que a própria conta enviou (avisos por SMTP), rascunhos e chats.
CONSULTA_PADRAO = "-in:sent -in:drafts -in:chats"
FOLGA = timedelta(days=2)
POR_PAGINA = 100


def carregar_credenciais(arquivo_token: str):
    """Lê o token gravado por `autorizar_gmail` e renova se expirou. Erros viram CredencialInvalida."""
    from google.auth.exceptions import GoogleAuthError, RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    caminho = Path(arquivo_token or "")
    if not arquivo_token or not caminho.is_file():
        raise CredencialInvalida("GMAIL_TOKEN_FILE ausente: rode `python -m worker.autorizar_gmail`")
    try:
        credenciais = Credentials.from_authorized_user_file(str(caminho), ESCOPOS)
        if not credenciais.valid:
            if not credenciais.refresh_token:
                raise CredencialInvalida("token sem refresh_token: rode `python -m worker.autorizar_gmail`")
            credenciais.refresh(Request())
            caminho.write_text(credenciais.to_json())
    except RefreshError as erro:
        raise CredencialInvalida(f"token expirado ou revogado ({type(erro).__name__})") from erro
    except (GoogleAuthError, ValueError) as erro:
        raise CredencialInvalida(f"token ilegível ({type(erro).__name__})") from erro
    except OSError as erro:
        raise FonteIndisponivel(f"sem acesso ao serviço de autenticação ({type(erro).__name__})") from erro
    return credenciais


def criar_servico(arquivo_token: str):
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=carregar_credenciais(arquivo_token), cache_discovery=False)


def consulta_com_corte(ultima_gravacao: Optional[datetime], consulta: str = CONSULTA_PADRAO) -> str:
    if ultima_gravacao is None:
        return consulta
    corte = int((ultima_gravacao - FOLGA).timestamp())
    return f"{consulta} after:{corte}"


def converter(bruto: dict) -> MensagemFonte:
    """Resposta de `messages.get(format='raw')` → MensagemFonte."""
    dados = base64.urlsafe_b64decode(bruto["raw"].encode("ascii") + b"=" * (-len(bruto["raw"]) % 4))
    msg = email.message_from_bytes(dados, policy=policy.compat32)
    recebida = datetime.fromtimestamp(int(bruto.get("internalDate", "0")) / 1000, tz=timezone.utc)
    mensagem = interpretar_email(msg, f"<{bruto['id']}@gmail.invalid>", recebida)
    veio_da_lista = any(LISTA in str(h).lower() for h in msg.get_all("X-BeenThere", []))
    return replace(mensagem, id_conversa=bruto["threadId"], veio_da_lista=veio_da_lista)


class LeitorGmail(FonteMensagens):
    def __init__(
        self,
        servico=None,
        arquivo_token: Optional[str] = None,
        ultima_gravacao: Optional[Callable[[], Optional[datetime]]] = None,
        consulta: str = CONSULTA_PADRAO,
    ):
        """`servico` é o cliente da API (injetado nos testes). Sem ele, monta a partir do token."""
        self._servico = servico
        self.arquivo_token = arquivo_token
        self.ultima_gravacao = ultima_gravacao or (lambda: None)
        self.consulta = consulta

    def _executar(self, requisicao):
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError

        try:
            return requisicao.execute(num_retries=2)
        except HttpError as erro:
            status = getattr(erro.resp, "status", None)
            if status in (401, 403):
                raise CredencialInvalida(f"Gmail recusou a credencial (HTTP {status})") from erro
            raise FonteIndisponivel(f"Gmail respondeu HTTP {status}") from erro
        except RefreshError as erro:
            raise CredencialInvalida(f"token expirado ou revogado ({type(erro).__name__})") from erro
        except (OSError, TimeoutError) as erro:
            raise FonteIndisponivel(f"Gmail fora do ar ({type(erro).__name__})") from erro

    def obter_mensagens(self) -> Iterable[MensagemFonte]:
        servico = self._servico or criar_servico(self.arquivo_token)
        mensagens = servico.users().messages()
        consulta = consulta_com_corte(self.ultima_gravacao(), self.consulta)
        pagina = None
        while True:
            resposta = self._executar(
                mensagens.list(userId="me", q=consulta, pageToken=pagina, maxResults=POR_PAGINA)
            )
            for ref in resposta.get("messages", []):
                bruto = self._executar(mensagens.get(userId="me", id=ref["id"], format="raw"))
                try:
                    yield converter(bruto)
                except (KeyError, ValueError) as erro:
                    # Mensagem que não dá para decodificar não derruba o ciclo; o id do Gmail não é dado pessoal.
                    log.warning("mensagem do Gmail %s ilegível, pulada (%s)", ref.get("id"), type(erro).__name__)
            pagina = resposta.get("nextPageToken")
            if not pagina:
                return
