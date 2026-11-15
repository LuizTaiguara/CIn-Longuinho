"""US-15 (ADR-010): entrar com a conta do CIn, sessão e sair."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from api import config as modulo_config
from api import sessao
from api.google import ClienteGoogle
from api.main import criar_app
from api.testes.conftest import fazer_config
from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, criar_item

SITE = "http://localhost:5173"


def iniciar(cliente, retorno="/meus-anuncios") -> str:
    resposta = cliente.get("/api/auth/google", params={"retorno": retorno}, follow_redirects=False)
    assert resposta.status_code == 302
    return parse_qs(urlparse(resposta.headers["location"]).query)["state"][0]


def concluir(cliente, estado, **params):
    return cliente.get(
        "/api/auth/google/callback", params={"state": estado, **params}, follow_redirects=False
    )


# --- Dado que tenho uma conta @cin.ufpe.br / Quando clico em "Entrar com a conta do CIn" -------


def test_conta_do_cin_e_autenticada_pelo_google_e_volta_ao_retorno(cliente, google, con):
    google.identidade_devolvida = {"email": AUTORA, "email_verified": True, "name": "Fic Teste"}

    estado = iniciar(cliente, "/itens/item_3?aba=x")
    resposta = concluir(cliente, estado, code="codigo-do-google")

    assert resposta.status_code == 302
    assert resposta.headers["location"] == f"{SITE}/itens/item_3?aba=x"
    cookie = resposta.headers["set-cookie"]
    assert "sessao_id=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    eu = cliente.get("/api/eu")
    assert eu.json() == {"autenticado": True, "nome": "Fic Teste"}


def test_o_sistema_nao_pede_nem_guarda_senha(cliente, google, con):
    google.identidade_devolvida = {"email": AUTORA, "email_verified": True, "name": "Fic"}
    concluir(cliente, iniciar(cliente), code="c")

    valor = cliente.cookies.get("sessao_id")
    dados = sessao._serializador(cliente.app.state.config).loads(valor)
    assert set(dados) == {"email", "nome"}
    tabelas = con.execute(
        "SELECT table_name FROM information_schema.columns WHERE column_name ILIKE '%senha%'"
    ).fetchall()
    assert tabelas == []


def test_url_do_google_pede_so_identidade_e_manda_o_dominio_como_dica(url_banco):
    config = fazer_config(url_banco, google_client_id="id-falso", google_client_secret="s")
    url = urlparse(ClienteGoogle(config).url_autorizacao("estado"))
    params = {k: v[0] for k, v in parse_qs(url.query).items()}

    assert url.netloc == "accounts.google.com"
    assert params["scope"] == "openid email profile"
    assert params["hd"] == "cin.ufpe.br"
    assert params["redirect_uri"] == "http://localhost:8000/api/auth/google/callback"
    assert params["state"] == "estado"


# --- Dado que tento entrar com uma conta de outro domínio --------------------------------------


@pytest.mark.parametrize(
    "identidade",
    [
        {"email": "fic.teste@gmail.com", "email_verified": True},
        {"email": "fic.teste@cin.ufpe.br.exemplo.com", "email_verified": True},
        {"email": "fic.teste@outro.cin.ufpe.br", "email_verified": True},
        {"email": AUTORA, "email_verified": False},
        {"email_verified": True},
    ],
)
def test_conta_de_fora_do_cin_e_recusada_pelo_servidor(cliente, google, con, identidade):
    google.identidade_devolvida = identidade

    resposta = concluir(cliente, iniciar(cliente), code="c")

    assert resposta.status_code == 302
    assert resposta.headers["location"] == f"{SITE}/login?erro=conta_fora_do_cin"
    assert "sessao_id=" not in resposta.headers.get("set-cookie", "")
    assert cliente.get("/api/eu").status_code == 401


def test_catalogo_continua_acessivel_depois_da_recusa(cliente, google, con):
    criar_item(con)
    google.identidade_devolvida = {"email": "fic.teste@gmail.com", "email_verified": True}
    concluir(cliente, iniciar(cliente), code="c")

    assert cliente.get("/api/itens").status_code == 200


# --- Falhas do fluxo ---------------------------------------------------------------------------


def test_quem_recusa_no_google_volta_com_erro_recusado(cliente, google, con):
    resposta = concluir(cliente, iniciar(cliente), error="access_denied")
    assert resposta.headers["location"] == f"{SITE}/login?erro=recusado"


def test_estado_invalido_volta_com_erro_e_nunca_json_403(cliente, google, con):
    for estado in ("forjado", "", iniciar(cliente) + "x"):
        resposta = concluir(cliente, estado, code="c")
        assert resposta.status_code == 302
        assert resposta.headers["location"] == f"{SITE}/login?erro=estado_invalido"


def test_estado_de_outro_navegador_e_recusado(cliente, google, con, config):
    google.identidade_devolvida = {"email": AUTORA, "email_verified": True}
    estado = iniciar(cliente)
    cliente.cookies.clear()  # o callback chega num navegador que não começou o login

    resposta = concluir(cliente, estado, code="c")

    assert resposta.headers["location"] == f"{SITE}/login?erro=estado_invalido"


def test_google_indisponivel_mantem_o_catalogo_e_avisa_com_honestidade(cliente, google, con):
    google.falhar = True
    resposta = concluir(cliente, iniciar(cliente), code="c")

    assert resposta.headers["location"] == f"{SITE}/login?erro=login_indisponivel"
    assert cliente.get("/api/itens").status_code == 200


def test_sem_credencial_do_google_o_login_avisa_que_esta_indisponivel(cliente, con):
    resposta = cliente.get("/api/auth/google", follow_redirects=False)
    assert resposta.status_code == 302
    assert resposta.headers["location"] == f"{SITE}/login?erro=login_indisponivel"


@pytest.mark.parametrize(
    "retorno",
    ["https://malicioso.example", "//malicioso.example", "/\\malicioso.example", "javascript:alert(1)", "itens", "", "/a\r\nb"],
)
def test_retorno_invalido_e_ignorado_e_o_login_termina_na_pagina_inicial(cliente, google, con, retorno):
    google.identidade_devolvida = {"email": AUTORA, "email_verified": True}

    resposta = concluir(cliente, iniciar(cliente, retorno), code="c")

    assert resposta.headers["location"] == f"{SITE}/"


# --- Login simulado (só desenvolvimento) -------------------------------------------------------


def test_login_simulado_cria_a_sessao_sem_google(url_banco, con):
    config = fazer_config(url_banco, login_simulado=AUTORA)
    with TestClient(criar_app(config)) as cliente:
        resposta = cliente.get("/api/auth/google", params={"retorno": "/cadastrar"}, follow_redirects=False)

        assert resposta.status_code == 302
        assert resposta.headers["location"] == f"{SITE}/cadastrar"
        assert cliente.get("/api/eu").json() == {"autenticado": True, "nome": "Pessoa de Teste"}


def test_api_recusa_subir_com_login_simulado_e_site_https(url_banco):
    with pytest.raises(modulo_config.ConfiguracaoInvalida):
        fazer_config(url_banco, login_simulado=AUTORA, site_url="https://achados.cin.ufpe.br")
    with pytest.raises(modulo_config.ConfiguracaoInvalida):
        modulo_config.carregar(
            {"DATABASE_URL": url_banco, "SESSAO_SEGREDO": "x", "LOGIN_SIMULADO": AUTORA, "SITE_URL": "https://a.b"}
        )


def test_login_simulado_so_aceita_conta_do_cin(url_banco):
    with pytest.raises(modulo_config.ConfiguracaoInvalida):
        fazer_config(url_banco, login_simulado="fic.teste@gmail.com")


def test_cookie_e_secure_quando_o_site_e_https(url_banco, con):
    config = fazer_config(url_banco, site_url="https://achados.cin.ufpe.br")
    with TestClient(criar_app(config), base_url="https://testserver") as cliente:
        cliente.app.state.google = type("G", (), {"configurado": True, "url_autorizacao": lambda s, e: "https://g"})()
        resposta = cliente.get("/api/auth/google", follow_redirects=False)
        assert "Secure" in resposta.headers["set-cookie"]


# --- GET /eu e POST /auth/logout ---------------------------------------------------------------


def test_eu_sem_sessao_devolve_401(cliente, con):
    resposta = cliente.get("/api/eu")
    assert resposta.status_code == 401
    conferir_resposta(resposta, "GET", "/eu")
    assert resposta.json()["codigo"] == "NAO_AUTENTICADO"


def test_eu_devolve_nome_e_nunca_o_email(entrar, con):
    resposta = entrar(AUTORA).get("/api/eu")
    conferir_resposta(resposta, "GET", "/eu")
    assert resposta.json() == {"autenticado": True, "nome": "Pessoa Fictícia"}
    assert AUTORA not in resposta.text


def test_sessao_expirada_volta_a_pedir_login(entrar, con, monkeypatch):
    cliente = entrar(AUTORA)
    monkeypatch.setattr(sessao, "DURACAO_SEGUNDOS", -1)
    assert cliente.get("/api/eu").status_code == 401


def test_logout_limpa_o_cookie(cliente, google, con):
    google.identidade_devolvida = {"email": AUTORA, "email_verified": True, "name": "Fic"}
    concluir(cliente, iniciar(cliente), code="c")
    assert cliente.get("/api/eu").status_code == 200

    resposta = cliente.post("/api/auth/logout")

    assert resposta.status_code == 204
    assert 'sessao_id=""' in resposta.headers["set-cookie"] or "Max-Age=0" in resposta.headers["set-cookie"]
    assert cliente.get("/api/eu").status_code == 401


def test_logout_sem_sessao_devolve_401(cliente, con):
    resposta = cliente.post("/api/auth/logout")
    assert resposta.status_code == 401
    conferir_resposta(resposta, "POST", "/auth/logout")
