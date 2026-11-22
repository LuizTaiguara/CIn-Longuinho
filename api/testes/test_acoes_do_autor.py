"""US-15: corrigir, encerrar e remover (ocultar) um anúncio próprio."""

from __future__ import annotations

import psycopg
import pytest

from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, OUTRA_PESSOA, criar_item, criar_mensagem


def eventos(con, numero) -> list[dict]:
    return con.execute("SELECT * FROM evento WHERE item_id = %s ORDER BY id", [numero]).fetchall()


# --- Dado que estou em um anúncio meu / Quando corrijo a descrição, o local ou a localização ----


def test_correcao_aparece_no_catalogo_e_fica_registrada_sem_apagar_o_anterior(entrar, con):
    numero = criar_item(con, descricao="Garrafa", local=["Grad 5"], localizacao="no local")
    cliente = entrar(AUTORA)

    resposta = cliente.patch(
        f"/api/itens/item_{numero}",
        json={"descricao": "Garrafa térmica azul", "local": ["Grad 5", "Anfiteatro"], "localizacao": "com quem achou"},
    )

    assert resposta.status_code == 200
    conferir_resposta(resposta, "PATCH", "/itens/{id}")
    publico = entrar(None).get(f"/api/itens/item_{numero}").json()
    assert publico["descricao"] == "Garrafa térmica azul"
    assert publico["local"] == ["Grad 5", "Anfiteatro"]
    assert publico["localizacao"] == "com quem achou"
    assert publico["data_atualizacao"] is not None
    (evento,) = eventos(con, numero)
    assert evento["tipo_evento"] == "edicao" and evento["fonte"] == "confirmação do autor"
    assert evento["detalhes"]["antes"] == {"descricao": "Garrafa", "local": ["Grad 5"], "localizacao": "no local"}
    assert evento["detalhes"]["depois"]["descricao"] == "Garrafa térmica azul"


def test_localizacao_com_um_setor_guarda_o_setor_e_outra_localizacao_o_descarta(entrar, con):
    numero = criar_item(con, localizacao="no local")
    cliente = entrar(AUTORA)

    com_setor = cliente.patch(f"/api/itens/item_{numero}", json={"localizacao": "com um setor", "setor": "SecGrad"}).json()
    assert com_setor["setor"] == "SecGrad"

    devolvido = cliente.patch(f"/api/itens/item_{numero}", json={"localizacao": "devolvido"}).json()
    assert devolvido["setor"] is None
    assert con.execute("SELECT setor FROM item WHERE id = %s", [numero]).fetchone()["setor"] is None


def test_autor_edita_item_encerrado_e_a_situacao_nao_muda(entrar, con):
    numero = criar_item(con, situacao="encerrado", fonte_encerramento="confirmação do autor")

    resposta = entrar(AUTORA).patch(f"/api/itens/item_{numero}", json={"descricao": "Casaco cinza"})

    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "encerrado"


def test_correcao_sem_mudanca_nao_gera_evento(entrar, con):
    numero = criar_item(con, descricao="Garrafa")
    entrar(AUTORA).patch(f"/api/itens/item_{numero}", json={"descricao": "Garrafa"})
    assert eventos(con, numero) == []


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"situacao": "encerrado"},
        {"oculto": False},
        {"autor_email": OUTRA_PESSOA},
        {"localizacao": "na portaria"},
        {"descricao": "   "},
        {"local": []},
        {"local": "Grad 5"},
        [],
    ],
)
def test_correcao_fora_do_contrato_devolve_400(entrar, con, corpo):
    numero = criar_item(con, localizacao="no local")
    resposta = entrar(AUTORA).patch(f"/api/itens/item_{numero}", json=corpo)
    assert resposta.status_code == 400, corpo
    conferir_resposta(resposta, "PATCH", "/itens/{id}")


def test_item_perdido_nao_recebe_localizacao(entrar, con):
    numero = criar_item(con, tipo="perdido")
    resposta = entrar(AUTORA).patch(f"/api/itens/item_{numero}", json={"localizacao": "no local"})
    assert resposta.status_code == 400


# --- Dado que estou em um anúncio meu, aberto ou reivindicado / Quando declaro que foi devolvido -


@pytest.mark.parametrize("situacao", ["aberto", "reivindicado"])
def test_encerrar_leva_a_encerrado_com_fonte_confirmacao_do_autor(entrar, con, situacao):
    numero = criar_item(con)
    if situacao == "reivindicado":
        con.execute("UPDATE item SET situacao = 'reivindicado' WHERE id = %s", [numero])

    resposta = entrar(AUTORA).post(f"/api/itens/item_{numero}/encerrar")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "POST", "/itens/{id}/encerrar")
    assert resposta.json()["situacao"] == "encerrado"
    assert resposta.json()["fonte_encerramento"] == "confirmação do autor"
    (evento,) = eventos(con, numero)
    assert evento["tipo_evento"] == "desfecho" and evento["aplicado"] is True
    assert evento["situacao_anterior"] == situacao and evento["situacao_nova"] == "encerrado"
    assert evento["fonte"] == "confirmação do autor"


def test_encerrar_item_ja_encerrado_registra_evento_sem_mudar_nada(entrar, con):
    numero = criar_item(con, situacao="encerrado", fonte_encerramento="terceiro")

    resposta = entrar(AUTORA).post(f"/api/itens/item_{numero}/encerrar")

    assert resposta.status_code == 200
    assert resposta.json()["fonte_encerramento"] == "terceiro"
    (evento,) = eventos(con, numero)
    assert evento["aplicado"] is False and evento["motivo_recusa"]


# --- Dado que estou em um anúncio meu / Quando peço a remoção ----------------------------------


def test_remover_tira_do_catalogo_mantem_o_bruto_e_fica_em_meus_anuncios(entrar, con):
    numero = criar_item(con, thread_id="thread-r")
    criar_mensagem(con, "thread-r")
    cliente = entrar(AUTORA)

    resposta = cliente.post(f"/api/itens/item_{numero}/ocultar")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "POST", "/itens/{id}/ocultar")
    assert entrar(None).get("/api/itens").json()["itens"] == []
    assert entrar(None).get(f"/api/itens/item_{numero}").status_code == 404
    assert con.execute("SELECT count(*) AS n FROM mensagem_bruta").fetchone()["n"] == 1
    meus = entrar(AUTORA).get("/api/eu/itens").json()
    assert meus[0]["id"] == f"item_{numero}" and meus[0]["oculto"] is True
    assert [e["tipo_evento"] for e in eventos(con, numero)] == ["ocultacao"]


def test_remover_de_novo_e_idempotente(entrar, con):
    numero = criar_item(con)
    cliente = entrar(AUTORA)
    cliente.post(f"/api/itens/item_{numero}/ocultar")

    resposta = cliente.post(f"/api/itens/item_{numero}/ocultar")

    assert resposta.status_code == 200
    assert len(eventos(con, numero)) == 1


def test_remocao_nao_pode_ser_desfeita(entrar, con):
    numero = criar_item(con)
    entrar(AUTORA).post(f"/api/itens/item_{numero}/ocultar")

    assert entrar(AUTORA).patch(f"/api/itens/item_{numero}", json={"oculto": False}).status_code in (400, 404)
    with pytest.raises(psycopg.errors.CheckViolation):
        con.execute("UPDATE item SET oculto = FALSE WHERE id = %s", [numero])


def test_item_oculto_nao_pode_ser_corrigido_nem_encerrado(entrar, con):
    numero = criar_item(con, oculto=True)
    cliente = entrar(AUTORA)
    assert cliente.patch(f"/api/itens/item_{numero}", json={"descricao": "Outra coisa"}).status_code == 404
    assert cliente.post(f"/api/itens/item_{numero}/encerrar").status_code == 404


# --- Dado que estou no anúncio de outra pessoa -------------------------------------------------


@pytest.mark.parametrize(
    "metodo,sufixo,corpo",
    [("PATCH", "", {"descricao": "Tomei o anúncio"}), ("POST", "/encerrar", None), ("POST", "/ocultar", None)],
)
def test_api_recusa_com_403_a_acao_no_anuncio_de_outra_pessoa(entrar, con, metodo, sufixo, corpo):
    numero = criar_item(con, autor_email=AUTORA, descricao="Garrafa")

    resposta = entrar(OUTRA_PESSOA).request(metodo, f"/api/itens/item_{numero}{sufixo}", json=corpo)

    assert resposta.status_code == 403
    conferir_resposta(resposta, metodo, f"/itens/{{id}}{sufixo}")
    linha = con.execute("SELECT descricao, situacao, oculto FROM item WHERE id = %s", [numero]).fetchone()
    assert linha == {"descricao": "Garrafa", "situacao": "aberto", "oculto": False}
    assert eventos(con, numero) == []


@pytest.mark.parametrize(
    "metodo,sufixo", [("PATCH", ""), ("POST", "/encerrar"), ("POST", "/ocultar")]
)
def test_acao_do_autor_sem_sessao_devolve_401(cliente, con, metodo, sufixo):
    numero = criar_item(con)
    resposta = cliente.request(metodo, f"/api/itens/item_{numero}{sufixo}", json={"descricao": "x"})
    assert resposta.status_code == 401
    conferir_resposta(resposta, metodo, f"/itens/{{id}}{sufixo}")


@pytest.mark.parametrize(
    "metodo,sufixo", [("PATCH", ""), ("POST", "/encerrar"), ("POST", "/ocultar")]
)
def test_acao_em_item_oculto_de_outra_pessoa_ou_inexistente_devolve_404(entrar, con, metodo, sufixo):
    oculto = criar_item(con, autor_email=AUTORA, oculto=True)
    for alvo in (f"item_{oculto}", "item_999", "retida_1", "x"):
        resposta = entrar(OUTRA_PESSOA).request(metodo, f"/api/itens/{alvo}{sufixo}", json={"descricao": "Outra"})
        assert resposta.status_code == 404, alvo


def test_autoria_vem_da_sessao_e_nunca_do_corpo(entrar, con):
    numero = criar_item(con, autor_email=AUTORA)
    resposta = entrar(OUTRA_PESSOA).patch(
        f"/api/itens/item_{numero}", json={"descricao": "Garrafa", "autor_email": OUTRA_PESSOA}
    )
    assert resposta.status_code == 403
