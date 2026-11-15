"""Acesso ao PostgreSQL pelo worker (psycopg 3).

O banco é o único ponto de integração com o site (invariante 8, ADR-001). Esta camada fica
duplicada com a da API nesta rodada; o ADR-008 prevê unificar em `shared/` depois.

Regras que este módulo materializa:
- `mensagem_bruta` é append-only: só INSERT, com `ON CONFLICT DO NOTHING` pelo `mensagem_id`.
- O estado "já processei" é a tabela `processamento` (chave: `Message-ID`). Reprocessar é apagar a
  linha dela, e é a única tabela em que DELETE é permitido. O worker nunca apaga nada.
- A trava de execução concorrente é um advisory lock de sessão com chave fixa.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parseaddr
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

from worker.fonte import MensagemFonte

# Chave fixa do pg_try_advisory_lock. Qualquer número serve, desde que só o worker o use.
CHAVE_TRAVA_WORKER = 50_2026_01

# Vocabulário de processamento.status (shared/AGENTS.md).
STATUS_PROCESSAMENTO = {"item", "evento", "quarentena", "ligada", "ignorada"}


class BancoIndisponivel(Exception):
    """Não foi possível falar com o banco. O worker encerra sem consumir mensagens."""


def extrair_email(remetente: str) -> str:
    """Devolve só o endereço do cabeçalho From, em minúsculas, ou '' se não houver endereço."""
    _, endereco = parseaddr(remetente or "")
    endereco = endereco.strip().lower()
    return endereco if "@" in endereco else ""


@dataclass
class MensagemBruta:
    """Uma linha de `mensagem_bruta`, com os metadados que o leitor guardou em `cabecalhos`."""

    id: int
    thread_id: str
    mensagem_id: str
    remetente: str
    assunto: str
    corpo: str
    data_envio: Optional[datetime]
    cabecalhos: Dict[str, Any] = field(default_factory=dict)

    @property
    def veio_da_lista(self) -> bool:
        return bool(self.cabecalhos.get("veio_da_lista", True))

    @property
    def em_resposta_a(self) -> Optional[str]:
        return self.cabecalhos.get("em_resposta_a")

    @property
    def anexos(self) -> List[Dict[str, Any]]:
        return list(self.cabecalhos.get("anexos") or [])

    @property
    def email_remetente(self) -> str:
        return extrair_email(self.remetente)


def conectar(database_url: str) -> psycopg.Connection:
    """Abre a conexão. Qualquer falha vira `BancoIndisponivel`, sem rastro com a URL (que tem senha)."""
    if not database_url:
        raise BancoIndisponivel("DATABASE_URL não está definida")
    try:
        return psycopg.connect(database_url, connect_timeout=5)
    except psycopg.Error as erro:
        raise BancoIndisponivel(f"não foi possível conectar ao banco ({type(erro).__name__})") from None


def _cabecalhos_da_fonte(msg: MensagemFonte) -> Dict[str, Any]:
    """Metadados que o pipeline precisa para reprocessar sem reler a fonte (Claim Check)."""
    return {
        "veio_da_lista": msg.veio_da_lista,
        "destinatarios": list(msg.destinatarios),
        "em_resposta_a": msg.em_resposta_a,
        "referencias": list(msg.referencias),
        "remetente_citado": msg.remetente_citado,
        "anexos": [
            {"nome_arquivo": a.nome_arquivo, "tipo_mime": a.tipo_mime, "tamanho": len(a.conteudo)}
            for a in msg.anexos
        ],
    }


class Repositorio:
    """Operações do worker sobre o banco. Recebe uma conexão já aberta."""

    def __init__(self, conexao: psycopg.Connection):
        self.conexao = conexao

    # ------------------------------------------------------------------ trava
    def tentar_trava(self) -> bool:
        """Tenta pegar a trava do worker. Fora de transação, para valer pela sessão inteira."""
        with self.conexao.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (CHAVE_TRAVA_WORKER,))
            obtida = bool(cur.fetchone()[0])
        self.conexao.commit()
        return obtida

    def liberar_trava(self) -> None:
        with self.conexao.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (CHAVE_TRAVA_WORKER,))
        self.conexao.commit()

    # ------------------------------------------------------------------ mensagem_bruta
    def gravar_mensagem_bruta(self, msg: MensagemFonte) -> bool:
        """Grava a mensagem como veio. Devolve True se era nova. Idempotente pelo Message-ID."""
        with self.conexao.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mensagem_bruta
                    (thread_id, mensagem_id, remetente, assunto, corpo, cabecalhos, data_envio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (mensagem_id) DO NOTHING
                RETURNING id
                """,
                (
                    msg.id_conversa,
                    msg.id_mensagem.strip(),
                    msg.remetente or "",
                    msg.assunto or "",
                    msg.corpo_texto or "",
                    json.dumps(_cabecalhos_da_fonte(msg), ensure_ascii=False),
                    msg.data_envio,
                ),
            )
            nova = cur.fetchone() is not None
        self.conexao.commit()
        return nova

    def _mensagens(self, onde: str, parametros: tuple) -> List[MensagemBruta]:
        with self.conexao.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT m.id, m.thread_id, m.mensagem_id, m.remetente, m.assunto, m.corpo,
                       m.data_envio, m.cabecalhos
                FROM mensagem_bruta m
                LEFT JOIN processamento p ON p.mensagem_id = m.mensagem_id
                WHERE {onde}
                ORDER BY m.thread_id, m.data_envio NULLS FIRST, m.id
                """,
                parametros,
            )
            linhas = cur.fetchall()
        return [
            MensagemBruta(
                id=l["id"],
                thread_id=l["thread_id"],
                mensagem_id=l["mensagem_id"],
                remetente=l["remetente"],
                assunto=l["assunto"] or "",
                corpo=l["corpo"] or "",
                data_envio=l["data_envio"],
                cabecalhos=l["cabecalhos"] or {},
            )
            for l in linhas
        ]

    def mensagens_pendentes(self) -> List[MensagemBruta]:
        """Mensagens gravadas e ainda sem `processamento`, em ordem de thread e de envio."""
        return self._mensagens("p.mensagem_id IS NULL", ())

    def mensagens_da_thread(self, thread_id: str) -> List[MensagemBruta]:
        """Todas as mensagens gravadas de uma thread, processadas ou não, em ordem de envio."""
        return self._mensagens("m.thread_id = %s", (thread_id,))

    # ------------------------------------------------------------------ processamento
    def marcar_processamento(self, mensagem: MensagemBruta, status: str) -> None:
        """Registra que a mensagem foi processada. Não faz commit: entra na transação da mensagem."""
        if status not in STATUS_PROCESSAMENTO:
            raise ValueError(f"status de processamento fora do vocabulário: {status!r}")
        with self.conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO processamento (mensagem_id, thread_id, status) VALUES (%s, %s, %s)",
                (mensagem.mensagem_id, mensagem.thread_id, status),
            )

    def status_processamento(self, mensagem_id: str) -> Optional[str]:
        with self.conexao.cursor() as cur:
            cur.execute("SELECT status FROM processamento WHERE mensagem_id = %s", (mensagem_id,))
            linha = cur.fetchone()
        return linha[0] if linha else None
