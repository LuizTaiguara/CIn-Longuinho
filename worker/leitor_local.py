"""Implementação do leitor de arquivos locais de e-mail (.eml).

Lê mensagens brutas de um diretório ou arquivo único sem rede e sem credenciais,
decodificando cabeçalhos RFC 5322 e estruturas MIME para instâncias de MensagemFonte (ADR-003, ADR-011).
"""
import email
from email import policy
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
from typing import Iterable, List, Optional, Tuple, Union

from worker.fonte import AnexoMensagem, FonteMensagens, MensagemFonte

# Padrão para identificar encaminhamentos no corpo (ADR-011 / caso 20)
PADRAO_ENCAMINHAMENTO = re.compile(
    r"(?:-{2,}\s*(?:Mensagem encaminhada|Mensaje reenviado|Forwarded message)\s*-{2,}[\s\S]*?"
    r"(?:De|From):\s*([^<\n]+<[^>\n]+>|[^\n]+))",
    re.IGNORECASE,
)


def _decodificar_cabecalho(valor: Optional[str]) -> str:
    """Decodifica cabeçalhos RFC 2047 com múltiplos encodings."""
    if not valor:
        return ""
    partes = decode_header(valor)
    resultado = []
    for bytes_ou_str, charset in partes:
        if isinstance(bytes_ou_str, bytes):
            charset_usado = charset or "utf-8"
            try:
                resultado.append(bytes_ou_str.decode(charset_usado, errors="replace"))
            except (LookupError, UnicodeDecodeError):
                resultado.append(bytes_ou_str.decode("latin1", errors="replace"))
        else:
            resultado.append(str(bytes_ou_str))
    return "".join(resultado).strip()


def _extrair_destinatarios(msg: email.message.EmailMessage) -> List[str]:
    """Extrai todos os destinatários dos cabeçalhos To e Cc."""
    destinatarios = []
    for header in ["To", "Cc"]:
        val = msg.get(header)
        if val:
            for item in str(val).split(","):
                dec = _decodificar_cabecalho(item)
                if dec:
                    destinatarios.append(dec)
    return destinatarios


def _extrair_corpo_e_anexos(msg: email.message.EmailMessage) -> Tuple[str, List[AnexoMensagem]]:
    """Percorre as partes MIME extraindo o corpo em texto plano e os anexos."""
    corpo_texto = ""
    anexos: List[AnexoMensagem] = []

    if msg.is_multipart():
        for parte in msg.walk():
            disposition = str(parte.get("Content-Disposition", ""))
            content_type = parte.get_content_type()
            filename = parte.get_filename()

            if filename or "attachment" in disposition.lower():
                nome_anexo = _decodificar_cabecalho(filename) if filename else "anexo"
                payload = parte.get_payload(decode=True) or b""
                anexos.append(
                    AnexoMensagem(
                        nome_arquivo=nome_anexo,
                        tipo_mime=content_type,
                        conteudo=payload,
                    )
                )
            elif content_type == "text/plain" and not corpo_texto:
                payload = parte.get_payload(decode=True)
                charset = parte.get_content_charset() or "utf-8"
                try:
                    corpo_texto = payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    corpo_texto = payload.decode("latin1", errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload is not None:
            if content_type == "text/plain":
                charset = msg.get_content_charset() or "utf-8"
                try:
                    corpo_texto = payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    corpo_texto = payload.decode("latin1", errors="replace")
            else:
                # Caso a mensagem inteira seja um binário/foto
                filename = msg.get_filename() or "anexo"
                anexos.append(
                    AnexoMensagem(
                        nome_arquivo=_decodificar_cabecalho(filename),
                        tipo_mime=content_type,
                        conteudo=payload,
                    )
                )

    return corpo_texto.strip(), anexos


def _extrair_remetente_original(remetente_cabecalho: str, corpo_texto: str) -> str:
    """Extrai o autor original do anúncio (ADR-011 / US-15).

    Se a mensagem for um encaminhamento explícito no corpo, extrai o remetente original
    em vez da pessoa que encaminhou.
    """
    match = PADRAO_ENCAMINHAMENTO.search(corpo_texto)
    if match:
        autor_extraido = match.group(1).strip()
        # Normaliza caso venha com quebras de linha
        autor_extraido = " ".join(autor_extraido.split())
        return autor_extraido
    return remetente_cabecalho


class LeitorArquivoLocal(FonteMensagens):
    """Lê arquivos .eml a partir do sistema de arquivos local."""

    def __init__(self, caminho_base: Union[str, Path]):
        self.caminho_base = Path(caminho_base)

    def _obter_arquivos_eml(self) -> List[Path]:
        """Obtém a lista de arquivos .eml ordenados."""
        if not self.caminho_base.exists():
            return []
        if self.caminho_base.is_file():
            return [self.caminho_base]
        return sorted(self.caminho_base.rglob("*.eml"))

    def _processar_arquivo(self, arquivo_path: Path) -> Optional[MensagemFonte]:
        """Carrega e decodifica um único arquivo .eml."""
        try:
            with open(arquivo_path, "rb") as f:
                msg = email.message_from_binary_file(f, policy=policy.compat32)
        except Exception:
            return None

        # Identificador único da mensagem
        id_mensagem = msg.get("Message-ID", f"<{arquivo_path.name}@local>")

        # Identificador da thread / conversa
        id_conversa = msg.get("X-Gmail-Thread-Id")
        if not id_conversa:
            # Recomposição de conversa via RFC 5322
            id_conversa = msg.get("In-Reply-To") or msg.get("References") or id_mensagem
            id_conversa = id_conversa.split()[0].strip()

        # Remetente e destinatários dos cabeçalhos
        remetente_header = _decodificar_cabecalho(msg.get("From", ""))
        destinatarios = _extrair_destinatarios(msg)
        assunto = _decodificar_cabecalho(msg.get("Subject", ""))

        # Data de envio
        data_header = msg.get("Date")
        if data_header:
            try:
                data_envio = parsedate_to_datetime(data_header)
            except Exception:
                from datetime import datetime, timezone
                data_envio = datetime.fromtimestamp(arquivo_path.stat().st_mtime, tz=timezone.utc)
        else:
            from datetime import datetime, timezone
            data_envio = datetime.fromtimestamp(arquivo_path.stat().st_mtime, tz=timezone.utc)

        # Corpo e Anexos
        corpo_texto, anexos = _extrair_corpo_e_anexos(msg)

        # Remetente original (ADR-011)
        remetente = _extrair_remetente_original(remetente_header, corpo_texto)

        # Verificação do header X-BeenThere para a lista de achados (ADR-011)
        been_there_headers = msg.get_all("X-BeenThere", [])
        veio_da_lista = any("achados-perdidos@cin.ufpe.br" in str(h).lower() for h in been_there_headers)
        # Se X-BeenThere não existir (ex: arquivo de teste sem cabeçalho de lista),
        # verifica se achados-perdidos está entre os destinatários
        if not been_there_headers:
            veio_da_lista = any("achados-perdidos@cin.ufpe.br" in d.lower() for d in destinatarios)

        em_resposta_a = msg.get("In-Reply-To")
        if em_resposta_a:
            em_resposta_a = em_resposta_a.strip()

        referencias_raw = msg.get("References")
        referencias = referencias_raw.split() if referencias_raw else []

        return MensagemFonte(
            id_mensagem=id_mensagem,
            id_conversa=id_conversa,
            remetente=remetente,
            destinatarios=destinatarios,
            assunto=assunto,
            corpo_texto=corpo_texto,
            data_envio=data_envio,
            veio_da_lista=veio_da_lista,
            em_resposta_a=em_resposta_a,
            referencias=referencias,
            anexos=anexos,
        )

    def obter_mensagens(self) -> Iterable[MensagemFonte]:
        """Lê os arquivos .eml do caminho e entrega instâncias de MensagemFonte."""
        arquivos = self._obter_arquivos_eml()
        for arq in arquivos:
            msg = self._processar_arquivo(arq)
            if msg:
                yield msg
