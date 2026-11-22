"""Configuração do worker, lida só de variáveis de ambiente (invariante 9).

O arquivo `.env` da raiz do repositório é carregado se existir (python-dotenv), sem sobrescrever o
que já está no ambiente. Nenhum valor sensível tem padrão no código.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
DIRETORIO_MIGRACOES = RAIZ_REPOSITORIO / "shared" / "migrations"

# Valores aceitos em WORKER_FONTE_MENSAGENS (nome do .env.example) e o apelido da linha de comando.
FONTES = {"arquivos_locais": "arquivos", "arquivos": "arquivos", "gmail": "gmail"}


def carregar_dotenv() -> None:
    """Carrega o `.env` da raiz, se existir. Nunca sobrescreve variável já definida."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependência listada em requirements.txt
        return
    load_dotenv(RAIZ_REPOSITORIO / ".env", override=False)


def url_banco_teste(database_url: str) -> str:
    """Deriva a URL do banco de teste do worker a partir da URL principal.

    `postgresql://u:s@h:5432/longuinho` vira `postgresql://u:s@h:5432/longuinho_teste_worker`.
    O sufixo `_worker` evita que a suíte da API e a do worker apaguem o banco uma da outra.
    """
    partes = urlsplit(database_url)
    nome = partes.path.lstrip("/") or "longuinho"
    return urlunsplit(partes._replace(path=f"/{nome}_teste_worker"))


@dataclass(frozen=True)
class Config:
    database_url: str
    fonte: str
    arquivos_dir: str
    intervalo_segundos: int

    @staticmethod
    def do_ambiente(ambiente: Optional[Mapping[str, str]] = None) -> "Config":
        env = os.environ if ambiente is None else ambiente
        fonte_bruta = env.get("WORKER_FONTE_MENSAGENS", "arquivos_locais").strip().lower()
        fonte = FONTES.get(fonte_bruta)
        if fonte is None:
            raise ValueError(
                f"WORKER_FONTE_MENSAGENS inválida: {fonte_bruta!r}. Use arquivos_locais ou gmail."
            )
        return Config(
            database_url=env.get("DATABASE_URL", ""),
            fonte=fonte,
            arquivos_dir=env.get("WORKER_ARQUIVOS_LOCAIS_DIR", "worker/corpus/casos"),
            intervalo_segundos=int(env.get("WORKER_INTERVALO_SEGUNDOS", "300")),
        )
