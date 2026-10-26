"""Interface e modelo de dados para a fonte de mensagens do worker.

Isola a origem dos dados (arquivos locais, Gmail, formulário web) do pipeline
de processamento (ADR-003). O pipeline consome esta abstração sem conhecer
a implementação concreta ou detalhes de SDKs externos.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List


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

    # Endereço de e-mail ou identificador de quem enviou
    remetente: str

    # Endereço de destino (ex: achados-perdidos@cin.ufpe.br)
    destinatario: str

    # Assunto original do e-mail
    assunto: str

    # Conteúdo textual decodificado em texto simples
    corpo_texto: str

    # Data e hora do envio com fuso horário
    data_envio: datetime

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
