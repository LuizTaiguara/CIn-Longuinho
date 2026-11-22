"""US-07: e-mail pronto para a lista, com o código que liga a conversa ao item."""

from __future__ import annotations

import re

import pytest

from api.rotas.cadastro import descricao_curta
from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, OUTRA_PESSOA, criar_item

SITE = "http://localhost:5173"


def cadastrar(entrar, **campos) -> tuple[str, str]:
    corpo = {"tipo": "achado", "descricao": "Garrafa térmica azul", "local": ["Grad 5", "Anfiteatro"],
             "localizacao": "com um setor", "setor": "SecGrad", **campos}
    item = entrar(AUTORA).post("/api/itens", json=corpo).json()
    meu = next(m for m in entrar(AUTORA).get("/api/eu/itens").json() if m["id"] == item["id"])
    return item["id"], meu["codigo"]


# --- Dado que acabei de cadastrar um item pelo site / Quando vejo a confirmação -----------------


def test_email_pronto_do_achado_traz_assunto_padronizado_e_o_corpo_completo(entrar, con):
    item_id, codigo = cadastrar(entrar)

    resposta = entrar(AUTORA).get(f"/api/itens/{item_id}/email-pronto")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "GET", "/itens/{id}/email-pronto")
    email = resposta.json()
    assert email["para"] == "achados-perdidos@cin.ufpe.br"
    assert email["assunto"] == f"[{codigo}] Achado: Garrafa térmica azul"
    assert email["corpo"] == (
        "Tipo: Achado\n"
        "Descrição: Garrafa térmica azul\n"
        "Local: Grad 5, Anfiteatro\n"
        "Onde está: com um setor (SecGrad)\n"
        f"Veja no catálogo: {SITE}/itens/{item_id}\n"
        "\n"
        f"Código do item: {codigo} (não apague, é ele que liga esta conversa ao catálogo)\n"
    )


def test_email_pronto_da_perda_nao_traz_onde_esta(entrar, con):
    item_id, codigo = cadastrar(entrar, tipo="perdido", descricao="Caderno verde de capa dura")

    email = entrar(AUTORA).get(f"/api/itens/{item_id}/email-pronto").json()

    assert email["assunto"] == f"[{codigo}] Perdido: Caderno verde de capa dura"
    assert "Onde está" not in email["corpo"]
    assert f"Código do item: {codigo}" in email["corpo"]


def test_codigo_vai_entre_colchetes_no_assunto_e_no_corpo(entrar, con):
    item_id, codigo = cadastrar(entrar)
    email = entrar(AUTORA).get(f"/api/itens/{item_id}/email-pronto").json()
    assert re.match(r"^\[AP-[A-Z2-7]{6}\] ", email["assunto"])
    assert email["corpo"].count(codigo) == 1


def test_email_pronto_nao_traz_o_endereco_de_quem_anunciou(entrar, con):
    item_id, _ = cadastrar(entrar)
    resposta = entrar(AUTORA).get(f"/api/itens/{item_id}/email-pronto")
    assert AUTORA not in resposta.text and "fic.teste" not in resposta.text


def test_descricao_longa_e_cortada_numa_palavra_inteira():
    longa = "Mochila preta da marca X com um chaveiro de pelúcia e um caderno de cálculo dentro"
    curta = descricao_curta(longa)
    assert curta.endswith("…")
    assert len(curta) <= 61
    assert longa.startswith(curta[:-1])
    assert descricao_curta("Garrafa\n azul") == "Garrafa azul"


# --- Dado que fechei o e-mail sem enviar / Quando acesso "Meus anúncios" -----------------------


def test_item_que_ainda_nao_foi_para_a_lista_pode_pedir_o_email_de_novo(entrar, con):
    item_id, _ = cadastrar(entrar)
    meu = entrar(AUTORA).get("/api/eu/itens").json()[0]
    assert meu["foi_para_a_lista"] is False
    assert entrar(AUTORA).get(f"/api/itens/{item_id}/email-pronto").status_code == 200


def test_marcacao_some_quando_o_worker_liga_a_thread_ao_item(entrar, con):
    item_id, _ = cadastrar(entrar)
    con.execute("UPDATE item SET thread_id = 'thread-ligada' WHERE id = %s", [int(item_id.removeprefix("item_"))])

    assert entrar(AUTORA).get("/api/eu/itens").json()[0]["foi_para_a_lista"] is True


# --- Quem pode pedir -----------------------------------------------------------------------------


def test_email_pronto_so_para_o_autor(entrar, con):
    item_id, _ = cadastrar(entrar)

    outra = entrar(OUTRA_PESSOA).get(f"/api/itens/{item_id}/email-pronto")
    sem_sessao = entrar(None).get(f"/api/itens/{item_id}/email-pronto")

    assert outra.status_code == 403
    conferir_resposta(outra, "GET", "/itens/{id}/email-pronto")
    assert sem_sessao.status_code == 401


@pytest.mark.parametrize("alvo", ["item_999", "retida_1", "x"])
def test_email_pronto_de_item_inexistente_devolve_404(entrar, con, alvo):
    assert entrar(AUTORA).get(f"/api/itens/{alvo}/email-pronto").status_code == 404


def test_email_pronto_de_item_da_lista_devolve_404(entrar, con):
    numero = criar_item(con, autor_email=AUTORA, origem="lista")
    resposta = entrar(AUTORA).get(f"/api/itens/item_{numero}/email-pronto")
    assert resposta.status_code == 404
    conferir_resposta(resposta, "GET", "/itens/{id}/email-pronto")


def test_email_pronto_de_item_oculto_devolve_404(entrar, con):
    item_id, _ = cadastrar(entrar)
    entrar(AUTORA).post(f"/api/itens/{item_id}/ocultar")
    assert entrar(AUTORA).get(f"/api/itens/{item_id}/email-pronto").status_code == 404
