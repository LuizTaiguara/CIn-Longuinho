"""US-15: "Meus anúncios", mensagem retida e classificação pelo autor."""

from __future__ import annotations

from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, OUTRA_PESSOA, antes, criar_item, criar_mensagem, criar_retida


def ids(resposta) -> list[str]:
    return [r["id"] for r in resposta.json()]


def retida_que_abre_thread(con, thread="thread-retida", remetente=f"Fic Teste <{AUTORA}>", **campos):
    mensagem = criar_mensagem(
        con, thread,
        remetente=remetente,
        assunto=campos.pop("assunto", "[Achados e Perdidos] Re: Casaco azul"),
        corpo=campos.pop("corpo", f"Deixei um casaco azul na Grad 3. Falar com {AUTORA}."),
        data_envio=campos.pop("data_envio", antes(hours=2)),
        **campos,
    )
    return criar_retida(con, mensagem, thread, motivo="direcao_ambigua")


# --- Dado que entrei com a minha conta / Quando acesso "Meus anúncios" -------------------------


def test_meus_anuncios_sem_sessao_devolve_401(cliente, con):
    resposta = cliente.get("/api/eu/itens")
    assert resposta.status_code == 401
    conferir_resposta(resposta, "GET", "/eu/itens")


def test_vejo_todos_os_itens_em_que_sou_autor_inclusive_os_da_lista(entrar, con):
    da_lista = criar_item(con, autor_email=AUTORA, origem="lista", data_anuncio=antes(days=30))
    do_site = criar_item(con, thread_id=None, codigo="AP-ABCDEF", origem="site", autor_email=AUTORA)
    criar_item(con, autor_email=OUTRA_PESSOA)

    resposta = entrar(AUTORA).get("/api/eu/itens")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "GET", "/eu/itens")
    assert ids(resposta) == [f"item_{do_site}", f"item_{da_lista}"]
    por_id = {r["id"]: r for r in resposta.json()}
    assert por_id[f"item_{da_lista}"]["origem"] == "lista"
    assert por_id[f"item_{da_lista}"]["foi_para_a_lista"] is True
    assert por_id[f"item_{do_site}"]["foi_para_a_lista"] is False
    assert por_id[f"item_{do_site}"]["codigo"] == "AP-ABCDEF"


def test_autoria_pela_lista_aceita_endereco_com_nome_e_maiusculas(entrar, con):
    numero = criar_item(con, autor_email=f"Fic Teste <{AUTORA.upper()}>")
    assert ids(entrar(AUTORA).get("/api/eu/itens")) == [f"item_{numero}"]


def test_item_oculto_continua_em_meus_anuncios_marcado_como_oculto(entrar, con):
    numero = criar_item(con, autor_email=AUTORA, oculto=True)

    item = entrar(AUTORA).get("/api/eu/itens").json()[0]

    assert item["id"] == f"item_{numero}"
    assert item["oculto"] is True
    assert item["fora_do_catalogo"] is False


# --- Dado que anunciei pela lista e minha mensagem ficou retida em quarentena ------------------


def test_retida_aparece_marcada_como_fora_do_catalogo_com_o_motivo(entrar, con):
    retida = retida_que_abre_thread(con)

    resposta = entrar(AUTORA).get("/api/eu/itens")

    conferir_resposta(resposta, "GET", "/eu/itens")
    registro = resposta.json()[0]
    assert registro["id"] == f"retida_{retida}"
    assert registro["fora_do_catalogo"] is True
    assert registro["motivo_retencao"] == "direcao_ambigua"
    assert registro["tipo"] is None and registro["situacao"] is None
    assert registro["descricao"] == "Casaco azul"


def test_retida_sem_assunto_mostra_o_comeco_do_corpo_mascarado(entrar, con):
    retida_que_abre_thread(con, assunto="", corpo=f"Perdi minha garrafa. {AUTORA} " + "x" * 300)

    descricao = entrar(AUTORA).get("/api/eu/itens").json()[0]["descricao"]

    assert descricao.startswith("Perdi minha garrafa. [e-mail mascarado]")
    assert AUTORA not in descricao
    assert len(descricao) <= 140 + len("[e-mail mascarado]")


def test_retida_de_uma_pessoa_nao_aparece_para_outra(entrar, con):
    retida_que_abre_thread(con)

    assert entrar(OUTRA_PESSOA).get("/api/eu/itens").json() == []
    assert entrar("fic.teste2@cin.ufpe.br").get("/api/eu/itens").json() == []


def test_retida_nao_aparece_no_catalogo(entrar, con):
    retida = retida_que_abre_thread(con)
    for quem in (None, AUTORA):
        assert entrar(quem).get("/api/itens").json()["itens"] == []
        assert entrar(quem).get(f"/api/itens/retida_{retida}").status_code == 404


def test_resposta_retida_na_thread_de_outra_pessoa_nao_aparece(entrar, con):
    criar_mensagem(con, "thread-de-b", remetente=OUTRA_PESSOA, corpo="Achei um casaco", data_envio=antes(hours=5))
    resposta_de_a = criar_mensagem(con, "thread-de-b", remetente=AUTORA, corpo="Acho que é meu!", data_envio=antes(hours=1))
    criar_retida(con, resposta_de_a, "thread-de-b")

    assert entrar(AUTORA).get("/api/eu/itens").json() == []


def test_retida_ja_resolvida_nao_aparece(entrar, con):
    mensagem = criar_mensagem(con, "thread-r", remetente=AUTORA)
    criar_retida(con, mensagem, "thread-r", resolvida=True)
    assert entrar(AUTORA).get("/api/eu/itens").json() == []


def test_lista_mistura_itens_e_retidas_do_mais_recente_para_o_mais_antigo(entrar, con):
    velho = criar_item(con, autor_email=AUTORA, data_anuncio=antes(days=3))
    retida = retida_que_abre_thread(con, data_envio=antes(days=1))
    novo = criar_item(con, autor_email=AUTORA, data_anuncio=antes(hours=1))

    assert ids(entrar(AUTORA).get("/api/eu/itens")) == [f"item_{novo}", f"retida_{retida}", f"item_{velho}"]


# --- Dado que estou numa mensagem minha que ficou retida / Quando indico perdido ou achado ------


def test_classificar_a_retida_vira_item_no_catalogo_com_evento_do_autor(entrar, con):
    retida = retida_que_abre_thread(con)
    mensagem_id = con.execute("SELECT mensagem_id FROM mensagem_bruta LIMIT 1").fetchone()["mensagem_id"]
    con.execute("INSERT INTO processamento (mensagem_id, thread_id, status) VALUES (%s, 'thread-retida', 'quarentena')", [mensagem_id])
    cliente = entrar(AUTORA)

    resposta = cliente.post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "perdido"})

    assert resposta.status_code == 201
    conferir_resposta(resposta, "POST", "/eu/retidas/{id}/classificar")
    item = resposta.json()
    assert item["tipo"] == "perdido" and item["situacao"] == "aberto"
    assert item["descricao"] == "Casaco azul"
    assert item["pode_gerir"] is True
    assert "[e-mail mascarado]" in item["texto_original"]
    assert [i["id"] for i in entrar(None).get("/api/itens").json()["itens"]] == [item["id"]]

    numero = int(item["id"].removeprefix("item_"))
    linha = con.execute("SELECT origem, thread_id, autor_email, data_anuncio FROM item WHERE id = %s", [numero]).fetchone()
    assert linha["origem"] == "lista" and linha["thread_id"] == "thread-retida" and linha["autor_email"] == AUTORA
    evento = con.execute("SELECT * FROM evento WHERE item_id = %s", [numero]).fetchone()
    assert evento["tipo_evento"] == "classificacao_pelo_autor"
    assert evento["fonte"] == "classificação pelo autor"
    assert evento["aplicado"] is True
    assert AUTORA not in str(evento["detalhes"])
    assert con.execute("SELECT resolvida FROM quarentena WHERE id = %s", [retida]).fetchone()["resolvida"] is True
    # Sinal para o worker rodar a extração: o controle de processamento da mensagem some.
    assert con.execute("SELECT count(*) AS n FROM processamento").fetchone()["n"] == 0
    # Nada é apagado: a mensagem bruta continua lá.
    assert con.execute("SELECT count(*) AS n FROM mensagem_bruta").fetchone()["n"] == 1


def test_retida_classificada_sai_da_lista_de_retidas(entrar, con):
    retida = retida_que_abre_thread(con)
    cliente = entrar(AUTORA)
    cliente.post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "achado"})

    registros = cliente.get("/api/eu/itens").json()

    assert len(registros) == 1
    assert registros[0]["id"].startswith("item_")
    assert registros[0]["fora_do_catalogo"] is False


def test_classificar_duas_vezes_devolve_409(entrar, con):
    retida = retida_que_abre_thread(con)
    cliente = entrar(AUTORA)
    cliente.post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "achado"})

    resposta = cliente.post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "achado"})

    assert resposta.status_code == 409
    conferir_resposta(resposta, "POST", "/eu/retidas/{id}/classificar")
    assert resposta.json()["codigo"] == "JA_CLASSIFICADA"


def test_alguem_tentando_classificar_a_retida_de_outra_pessoa_recebe_404(entrar, con):
    retida = retida_que_abre_thread(con)

    resposta = entrar(OUTRA_PESSOA).post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "achado"})
    inexistente = entrar(OUTRA_PESSOA).post("/api/eu/retidas/retida_999/classificar", json={"tipo": "achado"})

    assert resposta.status_code == 404
    conferir_resposta(resposta, "POST", "/eu/retidas/{id}/classificar")
    assert resposta.text == inexistente.text
    assert con.execute("SELECT resolvida FROM quarentena").fetchone()["resolvida"] is False


def test_classificar_resposta_na_thread_de_outra_pessoa_devolve_404(entrar, con):
    criar_mensagem(con, "thread-de-b", remetente=OUTRA_PESSOA, data_envio=antes(hours=5))
    resposta_de_a = criar_mensagem(con, "thread-de-b", remetente=AUTORA, data_envio=antes(hours=1))
    retida = criar_retida(con, resposta_de_a, "thread-de-b")

    resposta = entrar(AUTORA).post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "achado"})

    assert resposta.status_code == 404


def test_classificar_com_tipo_invalido_devolve_422(entrar, con):
    retida = retida_que_abre_thread(con)
    for corpo in ({"tipo": "doado"}, {}, {"tipo": "achado", "autor_email": AUTORA}):
        resposta = entrar(AUTORA).post(f"/api/eu/retidas/retida_{retida}/classificar", json=corpo)
        assert resposta.status_code == 422, corpo
        conferir_resposta(resposta, "POST", "/eu/retidas/{id}/classificar")


def test_classificar_sem_sessao_devolve_401(cliente, con):
    retida = retida_que_abre_thread(con)
    resposta = cliente.post(f"/api/eu/retidas/retida_{retida}/classificar", json={"tipo": "achado"})
    assert resposta.status_code == 401


def test_classificar_com_id_de_item_devolve_404(entrar, con):
    numero = criar_item(con, autor_email=AUTORA)
    resposta = entrar(AUTORA).post(f"/api/eu/retidas/item_{numero}/classificar", json={"tipo": "achado"})
    assert resposta.status_code == 404
