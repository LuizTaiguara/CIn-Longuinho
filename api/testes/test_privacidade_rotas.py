"""SCRUM-104: o endereço de quem anunciou não vaza em nenhuma rota.

Percorre TODAS as rotas da API, sem sessão, com a sessão de outra pessoa e com a sessão da
própria autora, sobre dados em que `autor_email`, `remetente`, o corpo e a descrição trazem
`fic.teste@cin.ufpe.br`. Afirma que nem o endereço nem a parte antes do @ aparecem em nenhum
corpo de resposta, em nenhum cabeçalho, nem nos logs capturados.

Rota nova sem roteiro aqui faz o teste falhar (`test_roteiro_cobre_todas_as_rotas_da_api`).
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import pytest

from api.testes.dados import AUTORA, OUTRA_PESSOA, antes, criar_item, criar_mensagem, criar_retida

AGULHAS = [AUTORA.lower(), "fic.teste", quote(AUTORA).lower(), "fic.teste%40"]


@pytest.fixture
def cenario(con):
    """Dados em que o endereço da autora aparece em todo lugar possível."""
    publicado = criar_item(
        con,
        thread_id="thread-publicada",
        autor_email=AUTORA,
        descricao=f"Garrafa azul, falar com {AUTORA}",
        localizacao="com um setor",
        setor=f"SecGrad {AUTORA}",
    )
    criar_mensagem(
        con, "thread-publicada",
        remetente=f"Fic Teste <{AUTORA}>",
        corpo=f"Achei uma garrafa azul. Contato: {AUTORA} ou (81) 9 9999-0000.",
        data_envio=antes(hours=3),
    )
    criar_mensagem(con, "thread-publicada", remetente=AUTORA, corpo=f"Ainda está comigo. {AUTORA}")
    oculto = criar_item(con, thread_id="thread-oculta", autor_email=AUTORA, oculto=True)
    encerrado = criar_item(con, autor_email=AUTORA, situacao="encerrado", fonte_encerramento="confirmação do autor")
    do_site = criar_item(con, thread_id=None, codigo="AP-ABCDEF", origem="site", autor_email=AUTORA)
    mensagem_retida = criar_mensagem(
        con, "thread-retida", remetente=f"<{AUTORA}>", assunto=f"Perdi? {AUTORA}", corpo=f"Alguém viu? {AUTORA}"
    )
    retida = criar_retida(con, mensagem_retida, "thread-retida")
    return {
        "item": f"item_{publicado}",
        "oculto": f"item_{oculto}",
        "encerrado": f"item_{encerrado}",
        "do_site": f"item_{do_site}",
        "retida": f"retida_{retida}",
    }


def roteiro(c: dict) -> list[tuple[str, str, str, dict]]:
    """(método, rota do contrato, URL, extras) para cada chamada a fazer."""
    chamadas = [
        ("GET", "/itens", "/api/itens", {}),
        ("GET", "/itens", "/api/itens?texto=garrafa", {}),
        ("GET", "/itens", f"/api/itens?texto={quote(AUTORA)}", {}),
        ("GET", "/itens", "/api/itens?texto=fic", {}),
        ("GET", "/itens", "/api/itens?local=Grad%205&tipo=achado&situacao=aberto", {}),
        ("GET", "/itens", "/api/itens?situacao=encerrado", {}),
        ("GET", "/itens", "/api/itens?limite=1&pagina=1", {}),
        ("GET", "/itens", "/api/itens?limite=1&pagina=2", {}),
        ("GET", "/itens", "/api/itens?limite=1&pagina=3", {}),
        ("GET", "/itens", f"/api/itens?tipo={quote(AUTORA)}", {}),
        ("GET", "/locais", "/api/locais", {}),
    ]
    for chave in ("item", "oculto", "encerrado", "do_site", "retida"):
        chamadas.append(("GET", "/itens/{id}", f"/api/itens/{c[chave]}", {}))
    return chamadas


SESSOES = [None, OUTRA_PESSOA, AUTORA]


def _conferir_sem_endereco(texto: str, onde: str) -> None:
    minusculo = texto.lower()
    for agulha in AGULHAS:
        assert agulha not in minusculo, f"vazou {agulha!r} em {onde}"


@pytest.mark.parametrize("quem", SESSOES, ids=["sem-sessao", "outra-pessoa", "autora"])
def test_nenhuma_rota_expoe_o_endereco_de_quem_anunciou(entrar, cenario, caplog, quem):
    caplog.set_level(logging.DEBUG)
    cliente = entrar(quem)

    for metodo, _, url, extras in roteiro(cenario):
        resposta = cliente.request(metodo, url, follow_redirects=False, **extras)
        onde = f"{metodo} {url} ({quem or 'sem sessão'})"
        assert resposta.status_code < 500, onde
        _conferir_sem_endereco(resposta.text, f"corpo de {onde}")
        for nome, valor in resposta.headers.items():
            _conferir_sem_endereco(f"{nome}: {valor}", f"cabeçalho de {onde}")

    _conferir_sem_endereco(caplog.text, "logs")
    for registro in caplog.records:
        _conferir_sem_endereco(registro.getMessage(), f"log {registro.name}")


def test_roteiro_cobre_todas_as_rotas_da_api(cliente, cenario):
    from fastapi.routing import APIRoute

    prefixo = cliente.app.state.config.api_prefix
    rotas_da_api = {
        (metodo, rota.path.removeprefix(prefixo))
        for rota in cliente.app.routes
        if isinstance(rota, APIRoute)
        for metodo in rota.methods
    }
    cobertas = {(metodo, rota) for metodo, rota, _, _ in roteiro(cenario)}

    assert rotas_da_api <= cobertas, f"rotas sem roteiro de privacidade: {sorted(rotas_da_api - cobertas)}"
