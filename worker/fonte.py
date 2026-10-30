"""Interface e modelo de dados para a fonte de mensagens do worker.

Isola a origem dos dados (arquivos locais, Gmail, formulário web) do pipeline
de processamento (ADR-003, ADR-011). O pipeline consome esta abstração sem conhecer
a implementação concreta ou detalhes de SDKs externos.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class AnexoMensagem:
    """Arquivo anexado a uma mensagem.

    Representa fotos ou documentos extraídos do corpo da mensagem.
    É imutável (frozen) para garantir integridade durante o pipeline.
    """
    nome_arquivo: str
    tipo_mime: str
    conteudo: bytes


@dataclass(frozen=True)
class MensagemFonte:
    """Estrutura padrão de uma mensagem entregue pela fonte ao pipeline.

    Contém os dados brutos necessários para gravação em mensagem_bruta
    e para os estágios seguintes de classificação e extração.
    """
    # Identificador único da mensagem (ex: Message-ID no padrão RFC 5322)
    id_mensagem: str

    # Identificador da thread/conversa para agrupamento de mensagens (ADR-005)
    id_conversa: str

    # E-mail do autor original do anúncio (e não de quem encaminhou, conforme ADR-011 e US-15)
    remetente: str

    # Lista de destinatários (To e Cc, cobrindo envios múltiplos/aninhados)
    destinatarios: List[str]

    # Assunto original do e-mail
    assunto: str

    # Conteúdo textual decodificado em texto simples
    corpo_texto: str

    # Data e hora do envio com fuso horário
    data_envio: datetime

    # Indica se a mensagem passou pela lista institucional (verificado via X-BeenThere, ADR-011)
    veio_da_lista: bool = True

    # Message-ID da mensagem à qual esta responde (In-Reply-To, útil para montagem de thread)
    em_resposta_a: Optional[str] = None

    # Lista de Message-IDs de referências anteriores da thread (References)
    referencias: List[str] = field(default_factory=list)

    # Lista de arquivos anexados (padrão: lista vazia)
    anexos: List[AnexoMensagem] = field(default_factory=list)


class FonteMensagens(ABC):
    """Interface abstrata para provedores de leitura de mensagens.

    Qualquer fonte (leitor de arquivos locais .eml, cliente Gmail ou API web)
    deve implementar esta interface para ser consumida pelo worker.
    """

    @abstractmethod
    def obter_mensagens(self) -> Iterable[MensagemFonte]:
        """Recupera mensagens disponíveis na fonte para processamento.

        Returns:
            Um iterável contendo as instâncias de MensagemFonte a processar.
        """
        pass
