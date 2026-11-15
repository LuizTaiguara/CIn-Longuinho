"""Entrada do worker: `python -m worker`.

Acorda, lê, grava e morre (ADR-003, worker/AGENTS.md). Em produção roda por cron com `--uma-vez`.
Sem `--uma-vez`, repete o ciclo a cada WORKER_INTERVALO_SEGUNDOS, só para conveniência local.
"""
import argparse
import logging
import sys
import time
from typing import Callable, List, Optional

from worker.banco import Repositorio, conectar
from worker.config import Config, carregar_dotenv
from worker.fonte import FonteMensagens
from worker.pipeline import Pipeline

log = logging.getLogger("worker")

SAIDA_OK = 0


def criar_fonte(nome: str, diretorio: str, repositorio: Optional[Repositorio] = None) -> FonteMensagens:
    if nome == "arquivos":
        from worker.leitor_local import LeitorArquivoLocal

        return LeitorArquivoLocal(diretorio)
    raise ValueError(f"fonte desconhecida: {nome!r}")


def executar_uma_vez(
    database_url: str,
    fabrica_fonte: Callable[[Repositorio], FonteMensagens],
    fabrica_pipeline: Callable[[Repositorio], Pipeline] = Pipeline,
) -> int:
    conexao = conectar(database_url)
    try:
        repo = Repositorio(conexao)
        resumo = fabrica_pipeline(repo).executar_ciclo(fabrica_fonte(repo))
        log.info("ciclo concluído: %s", resumo)
        return SAIDA_OK
    finally:
        conexao.close()


def analisar_argumentos(argv: Optional[List[str]], config: Config) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m worker", description="Worker de ingestão do Longuinho")
    parser.add_argument("--fonte", choices=["arquivos", "gmail"], default=config.fonte)
    parser.add_argument("--dir", default=config.arquivos_dir, help="pasta de .eml (fonte arquivos)")
    parser.add_argument("--uma-vez", action="store_true", help="roda um ciclo e sai (modo cron)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    carregar_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.do_ambiente()
    args = analisar_argumentos(argv, config)

    def fabrica_fonte(repo: Repositorio) -> FonteMensagens:
        return criar_fonte(args.fonte, args.dir, repo)

    while True:
        codigo = executar_uma_vez(config.database_url, fabrica_fonte)
        if args.uma_vez:
            return codigo
        time.sleep(config.intervalo_segundos)


if __name__ == "__main__":
    sys.exit(main())
