"""US-04 (parte do servidor) e regras de visibilidade do catálogo público (SCRUM-96).

Os nomes dos testes seguem os critérios de aceitação e os casos de falha do docs/BACKLOG.md.
"""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from api.main import criar_app
from api.testes.conftest import fazer_config
from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, OUTRA_PESSOA, antes, criar_item, criar_mensagem, criar_retida


def ids(resposta) -> list[str]:
    return [item["id"] for item in resposta.json()["itens"]]


# --- Dado que existem itens publicados / Quando acesso o catálogo, mesmo sem entrar -------------


def test_catalogo_sem_entrar_mostra_itens_do_mais_recente_para_o_mais_antigo(cliente, con):
    velho = criar_item(con, descricao="Casaco preto", data_anuncio=antes(days=3))
    novo = criar_item(con, descricao="Garrafa azul", data_anuncio=antes(hours=1))
    meio = criar_item(con, descricao="Crachá", data_anuncio=antes(days=1))

    resposta = cliente.get("/api/itens")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "GET", "/itens")
    assert ids(resposta) == [f"item_{novo}", f"item_{meio}", f"item_{velho}"]


def test_cada_item_mostra_descricao_local_data_e_situacao(cliente, con):
    criar_item(con, descricao="Garrafa azul", local=["Grad 5"], situacao="aberto")

    item = cliente.get("/api/itens").json()["itens"][0]

    assert item["descricao"] == "Garrafa azul"
    assert item["local"] == ["Grad 5"]
    assert item["data_registro"] == "2026-11-10T12:00:00Z"
    assert item["situacao"] == "aberto"


def test_data_atualizacao_e_nula_quando_o_item_nunca_mudou(cliente, con):
    criar_item(con)
    assert cliente.get("/api/itens").json()["itens"][0]["data_atualizacao"] is None


def test_data_atualizacao_vem_quando_o_item_mudou(cliente, con):
    numero = criar_item(con)
    con.execute("UPDATE item SET atualizado_em = criado_em + interval '1 hour' WHERE id = %s", [numero])
    assert cliente.get("/api/itens").json()["itens"][0]["data_atualizacao"] is not None


def test_setor_so_vem_quando_a_localizacao_e_com_um_setor(cliente, con):
    criar_item(con, descricao="Com setor", localizacao="com um setor", setor="SecGrad", data_anuncio=antes(hours=1))
    criar_item(con, descricao="Sem setor", localizacao="no local", setor="sobrou de antes")

    itens = {i["descricao"]: i for i in cliente.get("/api/itens").json()["itens"]}

    assert itens["Com setor"]["setor"] == "SecGrad"
    assert itens["Sem setor"]["setor"] is None


# --- Invariante 5: oculto e quarentena nunca saem ----------------------------------------------


def test_item_oculto_nunca_aparece_no_catalogo(cliente, con):
    criar_item(con, descricao="Garrafa visível")
    criar_item(con, descricao="Garrafa oculta", oculto=True)

    for query in ("", "?texto=garrafa", "?tipo=achado", "?situacao=aberto", "?local=Grad 5", "?limite=100"):
        resposta = cliente.get("/api/itens" + query)
        descricoes = [i["descricao"] for i in resposta.json()["itens"]]
        assert descricoes == ["Garrafa visível"], query
        assert resposta.json()["paginacao"]["total_itens"] == 1


def test_mensagem_em_quarentena_nunca_aparece_no_catalogo(cliente, con):
    mensagem = criar_mensagem(con, "thread-retida", assunto="Garrafa", corpo="Garrafa azul na Grad 5")
    criar_retida(con, mensagem, "thread-retida")

    for query in ("", "?texto=garrafa", "?tipo=achado", "?tipo=perdido", "?local=Grad 5"):
        assert cliente.get("/api/itens" + query).json()["itens"] == [], query


# --- Dado que busco por um termo ---------------------------------------------------------------


def test_busca_ignora_acento_e_maiuscula(cliente, con):
    criar_item(con, descricao="Óculos de grau com armação preta")

    for termo in ("oculos", "ÓCULOS", "Oculos", "armacao"):
        assert len(cliente.get("/api/itens", params={"texto": termo}).json()["itens"]) == 1, termo


def test_busca_casa_com_local_e_setor(cliente, con):
    criar_item(con, descricao="Mochila", local=["Laboratório de hardware"], localizacao="com um setor", setor="SecGrad")

    assert len(cliente.get("/api/itens", params={"texto": "laboratorio"}).json()["itens"]) == 1
    assert len(cliente.get("/api/itens", params={"texto": "secgrad"}).json()["itens"]) == 1


def test_busca_exige_todos_os_termos(cliente, con):
    criar_item(con, descricao="Garrafa azul")
    criar_item(con, descricao="Garrafa vermelha")

    resposta = cliente.get("/api/itens", params={"texto": "garrafa azul"})

    assert [i["descricao"] for i in resposta.json()["itens"]] == ["Garrafa azul"]


def test_busca_trata_curinga_como_texto(cliente, con):
    criar_item(con, descricao="Garrafa azul")
    assert cliente.get("/api/itens", params={"texto": "%"}).json()["itens"] == []
    assert cliente.get("/api/itens", params={"texto": "_"}).json()["itens"] == []


def test_sem_entrar_busca_nao_casa_com_o_texto_original(cliente, con):
    numero = criar_item(con, thread_id="thread-caderno", descricao="Estojo")
    criar_mensagem(con, "thread-caderno", corpo="Achei um estojo e um caderno de capa verde.")

    resposta = cliente.get("/api/itens", params={"texto": "caderno"})

    assert resposta.json()["itens"] == []
    assert len(cliente.get("/api/itens", params={"texto": "estojo"}).json()["itens"]) == 1
    assert numero


# --- Dado que filtro por local -----------------------------------------------------------------


def test_filtro_por_local_inclui_itens_que_citam_varios_locais(cliente, con):
    so_grad = criar_item(con, local=["Grad 5"], data_anuncio=antes(hours=2))
    varios = criar_item(con, local=["Grad 5", "Laboratório de hardware"], data_anuncio=antes(hours=1))
    criar_item(con, local=["Anfiteatro"])

    resposta = cliente.get("/api/itens", params={"local": "Grad 5"})

    assert ids(resposta) == [f"item_{varios}", f"item_{so_grad}"]


def test_filtro_por_local_ignora_acento_e_maiuscula(cliente, con):
    criar_item(con, local=["Laboratório de hardware"])
    assert len(cliente.get("/api/itens", params={"local": "laboratorio de HARDWARE"}).json()["itens"]) == 1


def test_filtro_por_local_compara_o_nome_inteiro(cliente, con):
    criar_item(con, local=["Grad 5"])
    assert cliente.get("/api/itens", params={"local": "Grad"}).json()["itens"] == []


# --- Dado que acesso o catálogo sem aplicar filtro ---------------------------------------------


def test_sem_filtro_achados_e_perdidos_vem_juntos_e_o_filtro_separa(cliente, con):
    achado = criar_item(con, tipo="achado", localizacao="no local", data_anuncio=antes(hours=1))
    perdido = criar_item(con, tipo="perdido")

    assert ids(cliente.get("/api/itens")) == [f"item_{perdido}", f"item_{achado}"]
    assert ids(cliente.get("/api/itens", params={"tipo": "achado"})) == [f"item_{achado}"]
    assert ids(cliente.get("/api/itens", params={"tipo": "perdido"})) == [f"item_{perdido}"]


def test_filtro_por_situacao(cliente, con):
    criar_item(con, situacao="aberto")
    reivindicado = criar_item(con, situacao="reivindicado")

    assert ids(cliente.get("/api/itens", params={"situacao": "reivindicado"})) == [f"item_{reivindicado}"]


# --- Encerrado por terceiro e reivindicado -----------------------------------------------------


def test_item_encerrado_por_terceiro_traz_a_fonte_e_continua_na_busca(cliente, con):
    criar_item(con, descricao="Fone de ouvido", situacao="encerrado", fonte_encerramento="terceiro")

    resposta = cliente.get("/api/itens", params={"texto": "fone"})

    item = resposta.json()["itens"][0]
    assert item["situacao"] == "encerrado"
    assert item["fonte_encerramento"] == "terceiro"


def test_item_reivindicado_traz_desde_quando_esta_nessa_situacao(cliente, con):
    numero = criar_item(con, situacao="aberto")
    con.execute("UPDATE item SET situacao = 'reivindicado' WHERE id = %s", [numero])
    desde = con.execute("SELECT data_situacao FROM item WHERE id = %s", [numero]).fetchone()["data_situacao"]

    item = cliente.get("/api/itens").json()["itens"][0]

    assert item["situacao"] == "reivindicado"
    assert datetime.fromisoformat(item["data_situacao"].replace("Z", "+00:00")) == desde


# --- Nada encontrado, termo genérico, paginação ------------------------------------------------


def test_nenhum_resultado_devolve_lista_vazia_e_nao_erro(cliente, con):
    criar_item(con, descricao="Garrafa")

    resposta = cliente.get("/api/itens", params={"texto": "guarda-chuva"})

    assert resposta.status_code == 200
    conferir_resposta(resposta, "GET", "/itens")
    assert resposta.json()["itens"] == []
    assert resposta.json()["paginacao"]["total_itens"] == 0


def test_catalogo_vazio_responde_200_com_lista_vazia(cliente, con):
    resposta = cliente.get("/api/itens")
    assert resposta.status_code == 200
    assert resposta.json() == {
        "itens": [],
        "paginacao": {"pagina_atual": 1, "total_paginas": 1, "total_itens": 0, "limite": 20},
    }


def test_termo_generico_volta_paginado(cliente, con):
    for n in range(25):
        criar_item(con, descricao=f"Casaco preto {n}", data_anuncio=antes(minutes=n))

    primeira = cliente.get("/api/itens", params={"texto": "preto"}).json()
    segunda = cliente.get("/api/itens", params={"texto": "preto", "pagina": 2}).json()

    assert len(primeira["itens"]) == 20
    assert primeira["paginacao"] == {"pagina_atual": 1, "total_paginas": 2, "total_itens": 25, "limite": 20}
    assert len(segunda["itens"]) == 5
    assert {i["id"] for i in primeira["itens"]}.isdisjoint({i["id"] for i in segunda["itens"]})


def test_limite_define_o_tamanho_da_pagina(cliente, con):
    for n in range(5):
        criar_item(con, data_anuncio=antes(minutes=n))

    resposta = cliente.get("/api/itens", params={"limite": 2, "pagina": 3}).json()

    assert len(resposta["itens"]) == 1
    assert resposta["paginacao"] == {"pagina_atual": 3, "total_paginas": 3, "total_itens": 5, "limite": 2}


def test_pagina_alem_da_ultima_vem_vazia(cliente, con):
    criar_item(con)
    resposta = cliente.get("/api/itens", params={"pagina": 9}).json()
    assert resposta["itens"] == []
    assert resposta["paginacao"]["pagina_atual"] == 9


def test_parametro_invalido_devolve_400_parametros_invalidos(cliente, con):
    for params in (
        {"tipo": "doado"},
        {"situacao": "devolvido"},
        {"pagina": "0"},
        {"pagina": "abc"},
        {"limite": "0"},
        {"limite": "101"},
        {"limite": "-1"},
    ):
        resposta = cliente.get("/api/itens", params=params)
        assert resposta.status_code == 400, params
        conferir_resposta(resposta, "GET", "/itens")
        assert resposta.json()["codigo"] == "PARAMETROS_INVALIDOS"


def test_banco_indisponivel_devolve_503_sem_rastro_de_excecao(url_banco):
    config = fazer_config("postgresql://ninguem:nada@127.0.0.1:1/nenhum", banco_timeout=0.5)
    with TestClient(criar_app(config)) as cliente:
        for caminho in ("/api/itens", "/api/itens/item_1", "/api/locais"):
            resposta = cliente.get(caminho)
            assert resposta.status_code == 503, caminho
            assert resposta.json()["codigo"] == "INDISPONIVEL"
            assert "Traceback" not in resposta.text
            assert "psycopg" not in resposta.text.lower()


# --- GET /itens/{id} ---------------------------------------------------------------------------


def test_detalhe_de_item_publicado(cliente, con):
    numero = criar_item(con, descricao="Garrafa azul", localizacao="no local")

    resposta = cliente.get(f"/api/itens/item_{numero}")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "GET", "/itens/{id}")
    corpo = resposta.json()
    assert corpo["id"] == f"item_{numero}"
    assert corpo["localizacao"] == "no local"
    assert corpo["pode_gerir"] is False
    assert corpo["texto_original"] is None


def test_oculto_inexistente_retida_e_id_malformado_devolvem_o_mesmo_404(cliente, con):
    oculto = criar_item(con, oculto=True)
    mensagem = criar_mensagem(con, "thread-retida")
    retida = criar_retida(con, mensagem, "thread-retida")

    respostas = [
        cliente.get(f"/api/itens/item_{oculto}"),
        cliente.get("/api/itens/item_999999"),
        cliente.get(f"/api/itens/retida_{retida}"),
        cliente.get("/api/itens/42"),
        cliente.get("/api/itens/item_0"),
        cliente.get("/api/itens/item_99999999999999999999999"),
    ]

    for resposta in respostas:
        assert resposta.status_code == 404
        conferir_resposta(resposta, "GET", "/itens/{id}")
    assert len({r.text for r in respostas}) == 1


def test_pode_gerir_so_para_quem_anunciou(entrar, con):
    numero = criar_item(con, autor_email=AUTORA)
    caminho = f"/api/itens/item_{numero}"

    assert entrar(None).get(caminho).json()["pode_gerir"] is False
    assert entrar(OUTRA_PESSOA).get(caminho).json()["pode_gerir"] is False
    assert entrar(AUTORA).get(caminho).json()["pode_gerir"] is True
    assert entrar(AUTORA.upper().replace("@CIN.UFPE.BR", "@cin.ufpe.br")).get(caminho).json()["pode_gerir"] is True


def test_pode_gerir_compara_o_endereco_inteiro(entrar, con):
    numero = criar_item(con, autor_email="fic.joana@cin.ufpe.br")
    assert entrar("fic.ana@cin.ufpe.br").get(f"/api/itens/item_{numero}").json()["pode_gerir"] is False


def test_cookie_de_outro_dominio_nao_conta_como_sessao(cliente, config, con):
    from api import sessao

    numero = criar_item(con, autor_email="fic.teste@gmail.com")
    cliente.cookies.set(config.session_cookie_name, sessao.assinar(config, "fic.teste@gmail.com", "X"))

    assert cliente.get(f"/api/itens/item_{numero}").json()["pode_gerir"] is False


def test_cookie_adulterado_nao_conta_como_sessao(cliente, config, con):
    numero = criar_item(con)
    cliente.cookies.set(config.session_cookie_name, "eyJlbWFpbCI6ImZpYy50ZXN0ZUBjaW4udWZwZS5iciJ9.x.y")
    assert cliente.get(f"/api/itens/item_{numero}").json()["pode_gerir"] is False


# --- GET /locais -------------------------------------------------------------------------------


def test_locais_devolve_so_os_ativos_em_ordem_com_nome_e_bloco(cliente, con):
    con.execute("UPDATE local SET ativo = FALSE WHERE nome = 'Anfiteatro'")
    try:
        resposta = cliente.get("/api/locais")
    finally:
        con.execute("UPDATE local SET ativo = TRUE WHERE nome = 'Anfiteatro'")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "GET", "/locais")
    nomes = [local["nome"] for local in resposta.json()]
    assert nomes[0] == "Grad 1"
    assert "Anfiteatro" not in nomes
    assert {"nome": "Gerinfra (sala B021)", "bloco": None} in resposta.json()
    assert all(set(local) == {"nome", "bloco"} for local in resposta.json())


def test_rotas_ficam_sob_o_prefixo_api(cliente, con):
    assert cliente.get("/itens").status_code == 404
    assert cliente.get("/api/itens").status_code == 200
