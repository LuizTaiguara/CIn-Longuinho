"""US-03, US-04 e US-05 / SCRUM-95: texto original só para quem entrou, mascarado no servidor."""

from __future__ import annotations

import pytest

from api import privacidade
from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, OUTRA_PESSOA, antes, criar_item, criar_mensagem

CORPO = (
    "Achei um caderno verde na Grad 5. Quem for o dono, falar comigo: "
    f"{AUTORA} ou (81) 9 9876-5432."
)


@pytest.fixture
def item_com_mensagem(con):
    numero = criar_item(con, thread_id="thread-caderno", descricao="Caderno")
    criar_mensagem(con, "thread-caderno", corpo="Resposta: é meu!", data_envio=antes(hours=1))
    criar_mensagem(con, "thread-caderno", corpo=CORPO, data_envio=antes(hours=5))
    return numero


# --- Dado que não entrei com a conta do CIn / Quando abro um item ------------------------------


def test_sem_entrar_o_texto_original_nao_vem_na_resposta_da_api(entrar, item_com_mensagem):
    resposta = entrar(None).get(f"/api/itens/item_{item_com_mensagem}")

    assert resposta.status_code == 200
    assert resposta.json()["texto_original"] is None
    assert "verde" not in resposta.text
    assert "9876" not in resposta.text


# --- Dado que entrei com a conta do CIn / Quando abro um item ----------------------------------


def test_quem_entrou_ve_o_texto_original_com_telefone_e_email_mascarados(entrar, item_com_mensagem):
    resposta = entrar(OUTRA_PESSOA).get(f"/api/itens/item_{item_com_mensagem}")

    conferir_resposta(resposta, "GET", "/itens/{id}")
    assert resposta.json()["texto_original"] == (
        "Achei um caderno verde na Grad 5. Quem for o dono, falar comigo: "
        "[e-mail mascarado] ou [telefone mascarado]."
    )


def test_email_no_corpo_aparece_mascarado_inclusive_para_o_autor(entrar, item_com_mensagem):
    resposta = entrar(AUTORA).get(f"/api/itens/item_{item_com_mensagem}")
    assert AUTORA not in resposta.text
    assert "[e-mail mascarado]" in resposta.json()["texto_original"]


def test_texto_original_e_o_da_primeira_mensagem_da_thread(entrar, item_com_mensagem):
    texto = entrar(OUTRA_PESSOA).get(f"/api/itens/item_{item_com_mensagem}").json()["texto_original"]
    assert texto.startswith("Achei um caderno")


def test_mensagem_que_nao_passou_pela_lista_nao_vira_texto_original(entrar, con):
    numero = criar_item(con, thread_id="thread-x")
    criar_mensagem(con, "thread-x", mensagem_id="<direta@teste.invalid>", corpo="Mensagem direta", data_envio=antes(days=1))
    criar_mensagem(con, "thread-x", corpo="Mensagem da lista", data_envio=antes(hours=1))
    con.execute(
        "INSERT INTO processamento (mensagem_id, thread_id, status) VALUES ('<direta@teste.invalid>', 'thread-x', 'ignorada')"
    )

    texto = entrar(OUTRA_PESSOA).get(f"/api/itens/item_{numero}").json()["texto_original"]

    assert texto == "Mensagem da lista"


def test_item_cadastrado_pelo_site_nao_tem_texto_original(entrar, con):
    numero = criar_item(con, thread_id=None, codigo="AP-ABCDEF", origem="site")
    assert entrar(OUTRA_PESSOA).get(f"/api/itens/item_{numero}").json()["texto_original"] is None


def test_item_sem_mensagem_gravada_tem_texto_original_nulo(entrar, con):
    numero = criar_item(con, thread_id="thread-sem-mensagem")
    assert entrar(OUTRA_PESSOA).get(f"/api/itens/item_{numero}").json()["texto_original"] is None


# --- Busca com sessão --------------------------------------------------------------------------


def test_quem_entrou_encontra_pelo_texto_original(entrar, item_com_mensagem):
    resposta = entrar(OUTRA_PESSOA).get("/api/itens", params={"texto": "verde"})
    assert [i["id"] for i in resposta.json()["itens"]] == [f"item_{item_com_mensagem}"]


def test_quem_entrou_nao_encontra_pelo_telefone_nem_pelo_email_do_texto(entrar, item_com_mensagem):
    for termo in ("9876-5432", "98765432", "fic.teste", AUTORA):
        assert entrar(OUTRA_PESSOA).get("/api/itens", params={"texto": termo}).json()["itens"] == [], termo


def test_busca_com_sessao_nao_usa_respostas_da_thread(entrar, item_com_mensagem):
    # "meu" só aparece na resposta, não na mensagem que abriu a thread.
    assert entrar(OUTRA_PESSOA).get("/api/itens", params={"texto": "meu!"}).json()["itens"] == []


# --- Regra de mascaramento: cada formato é um caso de teste ------------------------------------


@pytest.mark.parametrize(
    "telefone",
    [
        "(81) 9 9999-9999",
        "(81) 99999-9999",
        "(81)99999-9999",
        "81 99999-9999",
        "81 9 9999-9999",
        "81999999999",
        "+55 81 99999-9999",
        "+55 (81) 9 9999-9999",
        "+5581999999999",
        "5581999999999",
        "081 99999-9999",
        "99999-9999",
        "9 9999-9999",
        "9999-9999",
        "3271-8430",
        "81 9.9999.9999",
    ],
)
def test_telefone_em_formato_brasileiro_comum_sai_mascarado(telefone):
    assert privacidade.mascarar(f"ligue {telefone} depois") == "ligue [telefone mascarado] depois"


@pytest.mark.parametrize(
    "texto",
    ["Grad 5", "sala 2026", "R$ 2,00", "15/11/2026", "ramal 2134", "AP-K7F3Q2", "turma 2026.2"],
)
def test_numero_que_nao_e_telefone_fica_como_esta(texto):
    assert privacidade.mascarar(texto) == texto


def test_mascara_nada_quando_nao_ha_texto():
    assert privacidade.mascarar(None) is None
    assert privacidade.mascarar("") == ""
