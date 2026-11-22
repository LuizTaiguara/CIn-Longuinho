"""Entrada do worker: `python -m worker`.

Acorda, lê, grava e morre (ADR-003, worker/AGENTS.md). Em produção roda por cron com `--uma-vez`.
Sem `--uma-vez`, repete o ciclo a cada WORKER_INTERVALO_SEGUNDOS, só para conveniência local.

Códigos de saída:
  0  ciclo terminou, ou outra execução já estava em andamento (não é erro)
  1  a fonte falhou (credencial expirada, Gmail fora do ar); nada foi marcado como processado
  2  banco indisponível; nenhuma mensagem foi consumida
"""
import argparse
import logging
import os
import sys
import time
from typing import Callable, List, Optional

import psycopg

from worker.banco import BancoIndisponivel, Repositorio, conectar
from worker.config import Config, carregar_dotenv
from worker.fonte import CredencialInvalida, FonteIndisponivel, FonteMensagens
from worker.pipeline import Pipeline
from worker.registro import configurar_log

log = logging.getLogger("worker")

SAIDA_OK = 0
SAIDA_FONTE = 1
SAIDA_BANCO = 2


def criar_fonte(nome: str, diretorio: str, repositorio: Optional[Repositorio] = None) -> FonteMensagens:
    if nome == "arquivos":
        from worker.leitor_local import LeitorArquivoLocal

        return LeitorArquivoLocal(diretorio)
    if nome == "gmail":
        from worker.leitor_gmail import LeitorGmail

        return LeitorGmail(
            arquivo_token=os.environ.get("GMAIL_TOKEN_FILE") or "worker/.segredos/token.json",
            ultima_gravacao=repositorio.ultima_gravacao if repositorio is not None else None,
        )
    raise ValueError(f"fonte desconhecida: {nome!r}")


def executar_uma_vez(
    database_url: str,
    fabrica_fonte: Callable[[Repositorio], FonteMensagens],
    fabrica_pipeline: Callable[[Repositorio], Pipeline] = Pipeline,
) -> int:
    """Um ciclo completo, com trava e tratamento das falhas da US-01."""
    try:
        conexao = conectar(database_url)
    except BancoIndisponivel as erro:
        log.error("banco indisponível, encerrando sem consumir mensagens: %s", erro)
        return SAIDA_BANCO

    try:
        repo = Repositorio(conexao)
        if not repo.tentar_trava():
            log.info("outra execução do worker está em andamento; encerrando")
            return SAIDA_OK
        try:
            pipeline = fabrica_pipeline(repo)
            resumo = pipeline.executar_ciclo(fabrica_fonte(repo))
        except CredencialInvalida as erro:
            log.error("credencial da fonte expirada ou revogada; nada foi marcado: %s", erro)
            return SAIDA_FONTE
        except FonteIndisponivel as erro:
            log.error("fonte indisponível; o próximo ciclo tenta de novo: %s", erro)
            return SAIDA_FONTE
        finally:
            try:
                repo.liberar_trava()
            except psycopg.Error:
                pass  # a trava cai junto com a sessão
        log.info("ciclo concluído: %s", resumo)
        return SAIDA_OK
    except psycopg.OperationalError as erro:
        log.error("banco caiu durante o ciclo; o que não terminou continua pendente (%s)", type(erro).__name__)
        return SAIDA_BANCO
    finally:
        try:
            conexao.close()
        except psycopg.Error:
            pass


def analisar_argumentos(argv: Optional[List[str]], config: Config) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m worker", description="Worker de ingestão do Longuinho")
    parser.add_argument("--fonte", choices=["arquivos", "gmail"], default=config.fonte)
    parser.add_argument("--dir", default=config.arquivos_dir, help="pasta de .eml (fonte arquivos)")
    parser.add_argument("--uma-vez", action="store_true", help="roda um ciclo e sai (modo cron)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    carregar_dotenv()
    configurar_log()
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
