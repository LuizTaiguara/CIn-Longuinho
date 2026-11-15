"""Valida o worker contra o corpus e o gabarito do PO (SCRUM-90).

    python -m worker.avaliar [--dir worker/corpus/casos] [--sem-recriar]

Recria o banco de teste (DATABASE_URL_TESTE, padrão `<banco>_teste_worker`) a partir de
`shared/migrations/`, roda o pipeline inteiro sobre o corpus e imprime, por thread, esperado ×
obtido. O gabarito nunca é editado aqui: divergência é defeito do worker ou pergunta ao PO.

Regras de comparação (worker/corpus/README.md):
- `local` e `objeto` comparam por "contém", sem acento e sem maiúscula;
- `destino`: o gabarito diz `quarentena` para o aviso do caso 9, que não passou pela lista. Pela
  decisão do PO de 13/11/2026, ele fica `ignorada`. Os dois deixam a mensagem fora do catálogo, e o
  relatório conta como acerto, marcado com "(ignorada)".
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import psycopg

from worker.banco import Repositorio
from worker.config import RAIZ_REPOSITORIO, carregar_dotenv, url_banco_teste
from worker.leitor_local import LeitorArquivoLocal
from worker.migracoes import recriar_banco_de_teste
from worker.pipeline import Pipeline
from worker.texto import normalizar

GABARITO = RAIZ_REPOSITORIO / "worker" / "corpus" / "gabarito.json"
CORPUS = RAIZ_REPOSITORIO / "worker" / "corpus" / "casos"
CAMPOS = ["destino", "tipo", "situacao", "fonte_encerramento", "localizacao", "local", "objeto"]
# Campos que fazem `python -m worker.avaliar` sair com código 1 se divergirem.
CAMPOS_ESTRITOS = ["destino", "tipo", "situacao", "fonte_encerramento"]
PALAVRAS_VAZIAS = {"de", "da", "do", "das", "dos", "e", "com", "em", "na", "no", "um", "uma", "lado"}


@dataclass
class LinhaAvaliacao:
    caso: int
    thread_id: str
    esperado: Dict
    obtido: Dict
    acertos: Dict[str, Optional[bool]] = field(default_factory=dict)  # None = não se aplica
    respostas_na_lista: int = 0


def _contem_local(esperados: List[str], obtidos: List[str]) -> bool:
    if not esperados:
        return not obtidos
    obtidos_n = [normalizar(o) for o in obtidos]
    return all(any(normalizar(e) in o or o in normalizar(e) for o in obtidos_n if o) for e in esperados)


def _contem_objeto(esperado: str, descricao: Optional[str]) -> bool:
    texto = normalizar(descricao or "")
    palavras = [p for p in re.findall(r"[\w-]+", normalizar(esperado)) if p not in PALAVRAS_VAZIAS]
    return bool(texto) and all(p in texto for p in palavras)


def _obtido(conexao: psycopg.Connection, thread_id: str) -> Dict:
    repo = Repositorio(conexao)
    item = repo.item_da_thread(thread_id)
    if item is not None:
        return {
            "destino": "item",
            "tipo": item.tipo,
            "situacao": item.situacao,
            "fonte_encerramento": item.fonte_encerramento,
            "localizacao": item.localizacao,
            "setor": item.setor,
            "local": item.local,
            "objeto": item.descricao,
            "revisar": item.revisar,
        }
    with conexao.cursor() as cur:
        cur.execute("SELECT motivo_retencao FROM quarentena WHERE thread_id = %s ORDER BY id", (thread_id,))
        retida = cur.fetchone()
        cur.execute("SELECT DISTINCT status FROM processamento WHERE thread_id = %s", (thread_id,))
        status = {s for (s,) in cur.fetchall()}
    if retida:
        return {"destino": "quarentena", "motivo_retencao": retida[0]}
    if status == {"ignorada"}:
        return {"destino": "ignorada"}
    return {"destino": "pendente"}


def comparar(esperado: Dict, obtido: Dict) -> Dict[str, Optional[bool]]:
    acertos: Dict[str, Optional[bool]] = {c: None for c in CAMPOS}
    destino_ok = esperado["destino"] == obtido["destino"] or (
        esperado["destino"] == "quarentena" and obtido["destino"] == "ignorada"
    )
    acertos["destino"] = destino_ok
    if esperado["destino"] != "item":
        return acertos
    eh_item = obtido["destino"] == "item"
    acertos["tipo"] = eh_item and obtido["tipo"] == esperado.get("tipo")
    acertos["situacao"] = eh_item and obtido["situacao"] == esperado.get("situacao")
    acertos["fonte_encerramento"] = eh_item and obtido["fonte_encerramento"] == esperado.get("fonte_encerramento")
    localizacao_ok = eh_item and obtido["localizacao"] == esperado.get("localizacao")
    if localizacao_ok and esperado.get("setor"):
        localizacao_ok = normalizar(obtido.get("setor") or "") == normalizar(esperado["setor"])
    acertos["localizacao"] = localizacao_ok
    acertos["local"] = eh_item and _contem_local(esperado.get("local") or [], obtido.get("local") or [])
    acertos["objeto"] = eh_item and _contem_objeto(esperado.get("objeto") or "", obtido.get("objeto"))
    return acertos


def avaliar(url_teste: str, diretorio: Path = CORPUS, recriar: bool = True, pipeline_cls=Pipeline) -> List[LinhaAvaliacao]:
    if recriar:
        recriar_banco_de_teste(url_teste)
    gabarito = json.loads(GABARITO.read_text(encoding="utf-8"))
    with psycopg.connect(url_teste) as conexao:
        pipeline_cls(Repositorio(conexao)).executar_ciclo(LeitorArquivoLocal(diretorio))
        linhas = []
        for caso in gabarito:
            for thread in caso["threads"]:
                obtido = _obtido(conexao, thread["thread_id"])
                with conexao.cursor() as cur:
                    cur.execute(
                        "SELECT count(*) FROM mensagem_bruta WHERE thread_id = %s AND (cabecalhos->>'veio_da_lista')::boolean",
                        (thread["thread_id"],),
                    )
                    na_lista = cur.fetchone()[0]
                linhas.append(LinhaAvaliacao(
                    caso=caso["caso"],
                    thread_id=thread["thread_id"],
                    esperado=thread["esperado"],
                    obtido=obtido,
                    acertos=comparar(thread["esperado"], obtido),
                    respostas_na_lista=max(na_lista - 1, 0),
                ))
        conexao.commit()
    return linhas


def _fmt(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, list):
        return "[" + ", ".join(valor) + "]"
    return str(valor)


def imprimir(linhas: List[LinhaAvaliacao], saida=sys.stdout) -> None:
    for l in linhas:
        e, o = l.esperado, l.obtido
        marca = "OK " if all(v is not False for v in l.acertos.values()) else "ERR"
        print(f"{marca} caso {l.caso:>2} thread {l.thread_id}", file=saida)
        for campo in CAMPOS:
            ok = l.acertos[campo]
            if ok is None and campo != "destino":
                continue
            esperado = e.get(campo)
            obtido = o.get(campo)
            if campo == "destino" and o["destino"] == "ignorada":
                obtido = "ignorada (fora da lista)"
            if campo == "localizacao" and e.get("setor"):
                esperado = f"{esperado} · {e['setor']}"
                obtido = f"{obtido} · {o.get('setor')}"
            sinal = "✓" if ok else "✗"
            print(f"      {sinal} {campo:<19} esperado={_fmt(esperado):<40} obtido={_fmt(obtido)}", file=saida)
    print("\nAcertos por campo:", file=saida)
    for campo in CAMPOS:
        aplicaveis = [l.acertos[campo] for l in linhas if l.acertos[campo] is not None]
        print(f"  {campo:<19} {sum(aplicaveis):>2}/{len(aplicaveis)}", file=saida)


def main(argv=None) -> int:
    carregar_dotenv()
    parser = argparse.ArgumentParser(prog="python -m worker.avaliar")
    parser.add_argument("--dir", default=str(CORPUS))
    parser.add_argument("--sem-recriar", action="store_true", help="não recria o banco de teste")
    args = parser.parse_args(argv)
    url = os.environ.get("DATABASE_URL_TESTE") or url_banco_teste(
        os.environ.get("DATABASE_URL") or "postgresql://longuinho:longuinho@localhost:5432/longuinho"
    )
    linhas = avaliar(url, Path(args.dir), recriar=not args.sem_recriar)
    imprimir(linhas)
    falhas = [l for l in linhas if any(l.acertos[c] is False for c in CAMPOS_ESTRITOS)]
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
