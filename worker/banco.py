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


@dataclass
class Item:
    """Os campos de `item` que o worker lê para decidir transições."""

    id: int
    thread_id: Optional[str]
    codigo: Optional[str]
    tipo: str
    descricao: Optional[str]
    local: List[str]
    situacao: str
    localizacao: Optional[str]
    setor: Optional[str]
    autor_email: str
    fonte_encerramento: Optional[str]
    origem: str
    revisar: bool
    aviso_autor_enviado_em: Optional[datetime]


_COLUNAS_ITEM = (
    "id, thread_id, codigo, tipo::text AS tipo, descricao, local, situacao::text AS situacao, "
    "localizacao::text AS localizacao, setor, autor_email, fonte_encerramento, origem, revisar, "
    "aviso_autor_enviado_em"
)


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


    # ------------------------------------------------------------------ item, evento e quarentena
    # Toda escrita abaixo entra na transação da mensagem (sem commit aqui).
    def _item(self, onde: str, parametros: tuple) -> Optional[Item]:
        with self.conexao.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT {_COLUNAS_ITEM} FROM item WHERE {onde}", parametros)
            linha = cur.fetchone()
        if not linha:
            return None
        linha["local"] = list(linha["local"] or [])
        return Item(**linha)

    def item_da_thread(self, thread_id: str) -> Optional[Item]:
        return self._item("thread_id = %s", (thread_id,))

    def item_por_id(self, item_id: int) -> Optional[Item]:
        return self._item("id = %s", (item_id,))

    def item_por_codigo(self, codigo: str) -> Optional[Item]:
        return self._item("codigo = %s", (codigo,))

    def ligar_thread(self, item_id: int, thread_id: str) -> bool:
        """US-07: o e-mail pronto chegou à lista. Só liga item sem thread; devolve se ligou."""
        with self.conexao.cursor() as cur:
            cur.execute(
                "UPDATE item SET thread_id = %s, atualizado_em = NOW() WHERE id = %s AND thread_id IS NULL",
                (thread_id, item_id),
            )
            return cur.rowcount == 1

    def itens_para_avisar(self, a_partir_de) -> List[Item]:
        """Itens da lista cujo autor ainda não recebeu o aviso da US-15 (regras em worker/aviso.py)."""
        with self.conexao.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT {_COLUNAS_ITEM} FROM item i
                WHERE origem = 'lista' AND NOT oculto AND situacao <> 'encerrado'
                  AND aviso_autor_enviado_em IS NULL AND autor_email <> ''
                  AND data_anuncio >= %s
                  AND NOT EXISTS (SELECT 1 FROM evento e WHERE e.item_id = i.id
                                  AND e.tipo_evento IN ('classificacao_pelo_autor', 'aviso_autor'))
                ORDER BY id
                """,
                (a_partir_de,),
            )
            linhas = cur.fetchall()
        self.conexao.commit()
        for linha in linhas:
            linha["local"] = list(linha["local"] or [])
        return [Item(**l) for l in linhas]

    def reservar_aviso(self, item_id: int) -> bool:
        """Marca o aviso como enviado se ninguém marcou antes. Sem commit: entra na transação do envio."""
        with self.conexao.cursor() as cur:
            cur.execute(
                "UPDATE item SET aviso_autor_enviado_em = NOW() WHERE id = %s AND aviso_autor_enviado_em IS NULL",
                (item_id,),
            )
            return cur.rowcount == 1

    def criar_item(
        self,
        thread_id: str,
        tipo: str,
        descricao: str,
        autor_email: str,
        data_anuncio: Optional[datetime],
        revisar: bool,
        local: Optional[List[str]] = None,
        localizacao: Optional[str] = None,
        setor: Optional[str] = None,
    ) -> int:
        """Cria o item vindo da lista, sempre `aberto`. `localizacao` só vem preenchida quando o
        autor a declarou com uma frase explícita (invariante 3); senão fica NULL."""
        with self.conexao.cursor() as cur:
            cur.execute(
                """
                INSERT INTO item (thread_id, tipo, descricao, local, localizacao, setor, autor_email,
                                  origem, revisar, data_anuncio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'lista', %s, COALESCE(%s, NOW()))
                RETURNING id
                """,
                (thread_id, tipo, descricao, local or [], localizacao, setor, autor_email, revisar, data_anuncio),
            )
            return cur.fetchone()[0]

    def atualizar_campos(self, item_id: int, campos: Dict[str, Any]) -> None:
        """Atualiza descrição, local, localização e setor. Nunca `tipo` nem `situacao`."""
        permitidos = {"descricao", "local", "localizacao", "setor"}
        campos = {k: v for k, v in campos.items() if k in permitidos}
        if not campos:
            return
        atribuicoes = ", ".join(f"{k} = %s" for k in campos)
        with self.conexao.cursor() as cur:
            cur.execute(
                f"UPDATE item SET {atribuicoes}, atualizado_em = NOW() WHERE id = %s",
                (*campos.values(), item_id),
            )

    def tem_evento(self, item_id: int, tipo_evento: str, aplicado: Optional[bool] = None) -> bool:
        with self.conexao.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM evento WHERE item_id = %s AND tipo_evento = %s AND (%s::boolean IS NULL OR aplicado = %s) LIMIT 1",
                (item_id, tipo_evento, aplicado, aplicado),
            )
            return cur.fetchone() is not None

    def registrar_evento(
        self,
        item_id: int,
        tipo_evento: str,
        fonte: str,
        aplicado: bool,
        situacao_anterior: Optional[str] = None,
        situacao_nova: Optional[str] = None,
        motivo_recusa: Optional[str] = None,
        detalhes: Optional[dict] = None,
    ) -> int:
        with self.conexao.cursor() as cur:
            cur.execute(
                """
                INSERT INTO evento (item_id, tipo_evento, situacao_anterior, situacao_nova, fonte,
                                    aplicado, motivo_recusa, detalhes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    item_id,
                    tipo_evento,
                    situacao_anterior,
                    situacao_nova,
                    fonte,
                    aplicado,
                    motivo_recusa,
                    json.dumps(detalhes, ensure_ascii=False) if detalhes is not None else None,
                ),
            )
            return cur.fetchone()[0]

    def mudar_situacao(
        self, item_id: int, nova: str, fonte_encerramento: Optional[str] = None, revisar: Optional[bool] = None
    ) -> None:
        """Aplica uma transição já validada pelo chamador. O trigger do banco é só rede de segurança."""
        with self.conexao.cursor() as cur:
            cur.execute(
                """
                UPDATE item
                SET situacao = %s,
                    fonte_encerramento = COALESCE(%s, fonte_encerramento),
                    revisar = COALESCE(%s, revisar),
                    atualizado_em = NOW()
                WHERE id = %s
                """,
                (nova, fonte_encerramento, revisar, item_id),
            )

    def reter(self, mensagem: "MensagemBruta", motivo: str, grau_confianca: Optional[float]) -> int:
        with self.conexao.cursor() as cur:
            cur.execute(
                """
                INSERT INTO quarentena (thread_id, mensagem_bruta_id, motivo_retencao, grau_confianca)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (mensagem.thread_id, mensagem.id, motivo, grau_confianca),
            )
            return cur.fetchone()[0]

    def eventos_do_item(self, item_id: int) -> List[Dict[str, Any]]:
        with self.conexao.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT tipo_evento, fonte, aplicado, situacao_anterior::text AS situacao_anterior,
                       situacao_nova::text AS situacao_nova, motivo_recusa, detalhes
                FROM evento WHERE item_id = %s ORDER BY id
                """,
                (item_id,),
            )
            return cur.fetchall()
